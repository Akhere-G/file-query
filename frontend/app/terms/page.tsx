import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of use",
  description: "The rules for using the service.",
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-bold text-foreground">{title}</h2>
      <div className="space-y-3 text-muted-foreground leading-relaxed">
        {children}
      </div>
    </section>
  );
}

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto max-w-3xl px-4 md:px-6 pt-16 pb-24">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to home
        </Link>

        <h1 className="mt-8 text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">
          Terms of use
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Last updated: 7 October 2026
        </p>

        <div className="mt-10 space-y-10">
          <Section title="Agreeing to these terms">
            <p>
              The service is operated by Akhere (&quot;we&quot;,
              &quot;us&quot;). By creating an account or using the service, you
              agree to these terms and to our{" "}
              <Link href="/privacy" className="underline hover:text-foreground">
                privacy policy
              </Link>
              . If you do not agree, please do not use the service.
            </p>
          </Section>

          <Section title="What the service does">
            <p>
              You can upload documents into projects and ask questions about
              them. The service searches your files and uses an AI model to
              write answers from what it finds. The service is under active
              development, and features may change.
            </p>
          </Section>

          <Section title="Your account">
            <p>
              You must be at least 18 and give us accurate information. You are
              responsible for keeping your login details confidential and for
              activity under your account. Tell us promptly if you think your
              account has been misused.
            </p>
          </Section>

          <Section title="Your content">
            <p>
              You keep ownership of the files you upload and the questions you
              ask. You give us a limited licence to store, copy and process
              them, and to send the necessary parts to our service providers,
              only so that we can run the service for you.
            </p>
            <p>
              You confirm that you have all the rights and permissions needed to
              upload your content and to have it processed in this way,
              including any permission needed for personal data about other
              people.
            </p>
            <p>
              Please do not upload special category personal data (such as
              health or biometric data), criminal records, payment card details,
              passwords or other highly sensitive information. The service is
              not designed for it.
            </p>
            <p>
              The service is not a backup. Keep your own copies of any documents
              you upload.
            </p>
          </Section>

          <Section title="Acceptable use">
            <p>You must not:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>break the law or infringe anyone&apos;s rights;</li>
              <li>upload malware or content that is harmful or abusive;</li>
              <li>
                try to access other users&apos; data, or to disrupt, overload or
                probe the security of the service;
              </li>
              <li>
                bypass usage limits, or use automated tools to send requests
                without our permission.
              </li>
            </ul>
            <p>
              We may remove content or suspend accounts that break these rules.
              If you think content on the service infringes your rights, email
              us and we will review it.
            </p>
          </Section>

          <Section title="AI-generated answers">
            <p>
              Answers are written by an AI model using passages from your files.
              They can be incomplete, out of date or wrong, and the service may
              not find every relevant passage. Check important answers against
              your original documents before relying on them. Nothing the
              service produces is legal, medical, financial or other
              professional advice, and you are responsible for decisions you
              make using it.
            </p>
          </Section>

          <Section title="Usage limits and availability">
            <p>
              Accounts have a monthly limit on the number of messages. We may
              change limits, and we may change, pause or end features. We aim to
              keep the service running but cannot promise it will always be
              available or free of errors, and we may carry out maintenance
              without notice.
            </p>
          </Section>

          <Section title="Our intellectual property">
            <p>
              We and our licensors own the service&apos;s design, branding and
              software, except where the software is made available under an
              open-source licence, in which case that licence applies. These
              terms do not give you any rights in them beyond using the service
              as intended.
            </p>
          </Section>

          <Section title="Third-party services">
            <p>
              The service relies on third-party providers, including cloud
              hosting and AI services. We are not responsible for failures or
              changes outside our reasonable control, including those of these
              providers.
            </p>
          </Section>

          <Section title="Suspension and ending your use">
            <p>
              You can stop using the service and delete your account at any
              time. We may suspend or close your account if you break these
              terms or if we reasonably believe it is necessary to protect the
              service or other users, and we will give notice where we
              reasonably can.
            </p>
          </Section>

          <Section title="Warranties">
            <p>
              Except as set out in these terms, and to the extent the law
              allows, the service is provided &quot;as is&quot; and &quot;as
              available&quot;, and we give no warranty that it will be
              uninterrupted, error-free or fit for any particular purpose. If
              you are a consumer, your statutory rights are not affected.
            </p>
          </Section>

          <Section title="Limits on our liability">
            <p>
              Nothing in these terms excludes or limits our liability for death
              or personal injury caused by our negligence, for fraud or
              fraudulent misrepresentation, for breach of your rights under data
              protection law, or for anything else that cannot be excluded or
              limited by law.
            </p>
            <p>Subject to that, and to the extent the law allows:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                we are not liable for loss or damage that was not reasonably
                foreseeable when you started using the service;
              </li>
              <li>
                if you use the service for business purposes, we are not liable
                for loss of profit, revenue, business, goodwill or anticipated
                savings, or for indirect or consequential loss;
              </li>
              <li>
                we are not liable for loss or corruption of data you could have
                avoided by keeping your own copies, or for decisions you make
                relying on AI-generated answers; and
              </li>
              <li>
                our total liability to you for all claims arising from your use
                of the service will not exceed the greater of £100 and the total
                you paid us in the 12 months before the claim arose.
              </li>
            </ul>
          </Section>

          <Section title="Business users">
            <p>
              If you use the service for business purposes, you agree to
              compensate us for reasonable losses, costs and expenses (including
              reasonable legal fees) arising from a third-party claim caused by
              your content or your breach of these terms. We will tell you
              promptly about any such claim and let you take reasonable steps to
              deal with it.
            </p>
          </Section>

          <Section title="Complaints and disputes">
            <p>
              If you have a concern, please email us first so we can try to
              resolve it informally. These terms, and any dispute arising from
              them, are governed by the law of England and Wales. The courts of
              England and Wales have jurisdiction. If you are a consumer living
              in Scotland or Northern Ireland, you may also bring proceedings in
              your local courts.
            </p>
          </Section>

          <Section title="Changes to these terms">
            <p>
              We may update these terms. If the changes are significant, we will
              give you reasonable notice in the app or by email. Continuing to
              use the service after they take effect means you accept them.
            </p>
          </Section>

          <Section title="General">
            <p>
              These terms and our privacy policy are the whole agreement between
              us about the service. If any part is found unenforceable, the rest
              stays in force. If we do not enforce a right straight away, we can
              still enforce it later. We are not liable for delay or failure
              caused by events outside our reasonable control. You may not
              transfer your rights under these terms without our consent.
            </p>
          </Section>

          <Section title="Contact">
            <p>Questions about these terms? Email 101akhere5@gmail.com.</p>
          </Section>
        </div>
      </main>
    </div>
  );
}
