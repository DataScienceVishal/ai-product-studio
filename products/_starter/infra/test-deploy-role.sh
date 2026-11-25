#!/usr/bin/env bash
# T-65 static checks on deploy-role.bicep (the least-privilege role for id-github-deploy). No Azure, no network.
#
#   bash infra/test-deploy-role.sh [path/to/infra-dir]
#
# Text checks: they show the role covers every resource type the templates deploy and that it cannot grant access.
# They can't show how Azure authorizes each call; a missing action shows up as AuthorizationFailed on a real run.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dir="${1:-$here}"
role="$dir/deploy-role.bicep"
[ -f "$role" ] || { echo "no role file at $role"; exit 2; }
for f in main.bicep shared.bicep; do [ -f "$dir/$f" ] || { echo "missing $dir/$f"; exit 2; }; done

python3 -I - "$dir" <<'PY'
import re, sys, pathlib

d = pathlib.Path(sys.argv[1])
failed = 0
passed = 0

def ok(msg):
    global passed
    passed += 1
    print("ok   " + msg)

def bad(msg):
    global failed
    failed += 1
    print("FAIL " + msg)

def check(cond, msg):
    ok(msg) if cond else bad(msg)

role_src = (d / "deploy-role.bicep").read_text()
role_code = "\n".join(re.sub(r"\s//.*$", "", l) for l in role_src.splitlines() if not l.strip().startswith("//"))

def block(name):
    m = re.search(name + r":\s*\[(.*?)\n\s*\]", role_code, re.S)
    return re.findall(r"'([^']+)'", m.group(1)) if m else None

actions = block("actions")
not_actions = block("notActions")
check(actions is not None and len(actions) > 0, "role has an explicit actions list (%s entries)" % (len(actions) if actions else 0))
check(not_actions is not None and len(not_actions) > 0, "role has a notActions list")
actions = actions or []
not_actions = not_actions or []

# ---- no wildcard and nothing that grants access ------------------------------------------------------------------
check(not any(a.strip() == "*" for a in actions), "no bare '*' action")
check(not any("*" in a for a in actions), "no wildcard in any action (explicit list only)")
auth_writes = [a for a in actions if a.lower().startswith("microsoft.authorization/") and not a.lower().endswith("/read")]
check(not auth_writes, "no Microsoft.Authorization action other than read %s" % auth_writes)
check(not any("roleassignments" in a.lower() and not a.lower().endswith("/read") for a in actions),
      "roleAssignments is read-only in actions")
check(not any("roledefinitions" in a.lower() and not a.lower().endswith("/read") for a in actions),
      "roleDefinitions is read-only in actions")
check(not any("elevateaccess" in a.lower() for a in actions), "no elevateAccess in actions")
check(not any("federatedidentitycredentials" in a.lower() for a in actions), "no federatedIdentityCredentials in actions")
check(not any(a.lower().endswith("/listcredentials/action") or a.lower().endswith("/listkeys/action") for a in actions),
      "no listCredentials or listKeys (nothing reads secrets)")
# Secret-reading and remote-exec actions, by pattern (security review M5): none may appear.
deny_patterns = ("listkeys", "listcredentials", "listsecrets", "getsecret", "secrets/", "sharedkeys",
                 "getauthtoken", "/exec/", "regeneratekey", "listadminkeys", "listconnectionstrings", "generatetoken")
denied = [a for a in actions if any(p in a.lower() for p in deny_patterns)]
check(not denied, "no secret-reading or exec action (found %s)" % denied)
deletes = sorted(a for a in actions if a.lower().endswith("/delete"))
check(deletes == ["Microsoft.DBforPostgreSQL/flexibleServers/firewallRules/delete"],
      "the only delete is the runner firewall rule (found %s)" % deletes)
check("Microsoft.Authorization/*/write" in not_actions, "notActions denies Microsoft.Authorization/*/write")
check("Microsoft.Authorization/elevateAccess/action" in not_actions, "notActions denies elevateAccess")
check(len(set(actions)) == len(actions), "no duplicate actions")
check(re.search(r"dataActions:\s*\[\s*\]", role_code) is not None, "no dataActions")

# ---- scope and identity -------------------------------------------------------------------------------------------
check(re.search(r"targetScope\s*=\s*'resourceGroup'", role_code) is not None, "targetScope is resourceGroup")
m = re.search(r"assignableScopes:\s*\[(.*?)\]", role_code, re.S)
scopes = [s.strip() for s in m.group(1).split() if s.strip()] if m else []
check(scopes == ["resourceGroup().id"], "assignableScopes is resourceGroup().id only (found %s)" % scopes)
check(re.search(r"name:\s*guid\(resourceGroup\(\)\.id,", role_code) is not None, "role name is a deterministic guid of the resource group")
check(re.search(r"param\s+assign\s+bool\s*=\s*false", role_code) is not None, "assignment parameter 'assign' defaults to false")
check(re.search(r"roleAssignments@[^']+'\s*=\s*if\s*\(assign\)", role_code) is not None, "role assignment is conditional on assign")
check(re.search(r"principalType:\s*'ServicePrincipal'", role_code) is not None, "assignment principalType is ServicePrincipal")
check("Contributor" not in role_code and "b24988ac-6180-42a0-ab88-20f7382dd24c" not in role_code, "no Contributor role id used")

# ---- every deployed resource type is covered by an action ---------------------------------------------------------
decl = re.compile(r"^resource\s+\w+\s+'([^'@]+)@[^']+'\s*=\s*(existing\s*=\s*)?(?:if\b[^{]*)?\{", re.M)
needs = {}  # type -> set of required verbs
exempt = {"Microsoft.Authorization/roleAssignments"}  # shared.bicep pullRole, behind grantPullRole=false (Vishal grants AcrPull)
bicep_files = sorted(str(p.relative_to(d)) for p in d.rglob("*.bicep") if p.name != "deploy-role.bicep")
check("modules/postgres.bicep" in bicep_files, "templates found: %s" % bicep_files)
for f in bicep_files:
    text = (d / f).read_text()
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    found = decl.findall(text)
    check(len(found) > 0, "%s: found %d resource declarations" % (f, len(found)))
    for rtype, existing in found:
        verb = "read" if existing else "write"
        needs.setdefault(rtype, set()).add(verb)
        if not existing:
            needs[rtype].add("read")
for rtype, verbs in sorted(needs.items()):
    if rtype in exempt:
        ok("%s is exempt (conditional, granted by Owner; never by the deployer)" % rtype)
        continue
    for verb in sorted(verbs):
        want = "%s/%s" % (rtype, verb)
        check(want.lower() in (a.lower() for a in actions), "covered: %s" % want)

# ---- workflow `az` commands that need an action not tied to a Bicep type ------------------------------------------
extra = [
    "Microsoft.Resources/deployments/write", "Microsoft.Resources/deployments/read",
    "Microsoft.Resources/deployments/validate/action", "Microsoft.Resources/deployments/whatIf/action",
    "Microsoft.Resources/deployments/operationStatuses/read",
    "Microsoft.Resources/subscriptions/resourceGroups/read",
    "Microsoft.Resources/subscriptions/resourceGroups/resources/read",
    "Microsoft.ContainerRegistry/registries/push/write", "Microsoft.ContainerRegistry/registries/pull/read",
    "Microsoft.App/jobs/start/action", "Microsoft.App/jobs/executions/read",
    "Microsoft.App/containerApps/revisions/read", "Microsoft.App/containerApps/revisions/activate/action",
    "Microsoft.App/containerApps/revisions/deactivate/action", "Microsoft.App/managedEnvironments/join/action",
    "Microsoft.ManagedIdentity/userAssignedIdentities/assign/action",
    "Microsoft.Authorization/roleAssignments/read", "Microsoft.CostManagement/query/read",
    "Microsoft.DBforPostgreSQL/flexibleServers/firewallRules/delete",
]
lower = {a.lower() for a in actions}
for a in extra:
    check(a.lower() in lower, "workflow step action present: %s" % a)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
PY
