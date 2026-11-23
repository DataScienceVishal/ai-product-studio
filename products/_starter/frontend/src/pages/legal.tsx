import { Card } from "../ui";

function Draft() {
  return (
    <p className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900" role="note">
      DRAFT for review. Not legal advice. Each product replaces this text before any public launch.
    </p>
  );
}

export function Privacy() {
  return (
    <Card title="Privacy notice (DRAFT)">
      <Draft />
      <div className="space-y-3 text-slate-700">
        <p><strong>What we keep.</strong> Your company name, the email addresses and roles of your team, a scrambled
          (hashed) form of each password, the notes you write and their AI summaries, your plan, and how many AI tokens you use.</p>
        <p><strong>Why.</strong> To run the service you signed up for, to secure your account, and to bill you.</p>
        <p><strong>Who processes it.</strong> Our hosting provider (Microsoft Azure, UK region), Microsoft's Azure OpenAI
          service for AI summaries, and our payment provider once payments are switched on. Each processes data under its own
          data-protection terms. Microsoft may keep AI prompts and answers for up to 30 days to detect abuse, and some
          Azure OpenAI deployment types process data outside the UK; each product states which one it uses.</p>
        <p><strong>How long.</strong> Until you delete your account. Expired sign-in sessions and used links are removed
          within days; usage records after 13 months.</p>
        <p><strong>Your rights.</strong> Download your data or delete it at any time from Settings. Account owners can
          delete the whole company account; members can leave and delete their own sign-in.</p>
        <p><strong>Questions and complaints.</strong> Contact us at the support address each product lists here. You can
          also complain to the UK Information Commissioner's Office (ico.org.uk) or the data-protection authority where you live.</p>
      </div>
    </Card>
  );
}

export function Terms() {
  return (
    <Card title="Terms (DRAFT)">
      <Draft />
      <div className="space-y-3 text-slate-700">
        <p>The service is provided as it is during the trial. You are responsible for what you put into it and for
          checking AI output before relying on it.</p>
        <p>Paid plans renew monthly until cancelled. You can cancel at any time by deleting your account, which also
          cancels the subscription with our payment provider.</p>
      </div>
    </Card>
  );
}
