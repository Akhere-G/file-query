import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy policy",
  description: "How your files, questions and account details are handled.",
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

export default function PrivacyPage() {
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
          Privacy policy
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Last updated: 7 October 2026
        </p>

        <div className="mt-10 space-y-10">
          <Section title="Who we are">
            <p>
              This service is operated by Akhere (&quot;we&quot;,
              &quot;us&quot;). We are the controller of the personal data
              described in this policy. You can contact us at
              101akhere5@gmail.com.
            </p>
          </Section>

          <Section title="What we collect">
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong className="text-foreground">Account details:</strong>{" "}
                your email address and a securely hashed password.
              </li>
              <li>
                <strong className="text-foreground">Your files:</strong> the
                documents you upload, the text extracted from them, the chunks
                that text is split into, and the numerical embeddings we create
                from those chunks.
              </li>
              <li>
                <strong className="text-foreground">Your conversations:</strong>{" "}
                the questions you ask, the answers you receive, and which
                passages were used to produce each answer.
              </li>
              <li>
                <strong className="text-foreground">
                  Usage and technical data:
                </strong>{" "}
                how many messages you send each month, and standard server logs
                such as timestamps and error details.
              </li>
            </ul>
          </Section>

          <Section title="How and why we use it">
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong className="text-foreground">
                  To provide the service
                </strong>{" "}
                (storing your files, searching them and answering your
                questions). Our basis is performing our contract with you.
              </li>
              <li>
                <strong className="text-foreground">
                  To keep the service secure, enforce usage limits and prevent
                  misuse, and to diagnose and fix faults.
                </strong>{" "}
                Our basis is our legitimate interests in running a safe and
                reliable service.
              </li>
              <li>
                <strong className="text-foreground">
                  To meet legal obligations
                </strong>{" "}
                and respond to lawful requests.
              </li>
            </ul>
            <p>
              We do not sell your personal data and we do not use it for
              advertising.
            </p>
          </Section>

          <Section title="How AI is used">
            <p>
              To answer a question, we send the text of your question, relevant
              parts of your conversation and the passages retrieved from your
              files to Amazon Bedrock, which rewrites the question, creates
              embeddings and generates the answer. We do not use your content to
              train AI models. AWS states in its Bedrock documentation that
              customer prompts and responses are not used to train the
              underlying models.
            </p>
            <p>
              Answers are produced automatically but do not make decisions about
              you that have legal or similarly significant effects.
            </p>
          </Section>

          <Section title="Who we share data with">
            <p>
              We use the following providers as processors, under contracts that
              only allow them to handle your data to provide their services to
              us:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                Google Cloud Platform (GCP) for our database and hosting, in the
                europe-west1 region (Belgium).
              </li>
              <li>
                Amazon Web Services (AWS) for AI processing through Amazon
                Bedrock, and for encrypted file storage in eu-north-1
                (Stockholm).
              </li>
            </ul>
            <p>
              We may also disclose data where the law requires it, or to protect
              our rights, users or the public from harm.
            </p>
          </Section>

          <Section title="International transfers">
            <p>
              Your data is stored in the European Economic Area, which the UK
              recognises as providing adequate data protection. If a provider
              processes data elsewhere, we rely on approved safeguards, such as
              the UK International Data Transfer Agreement or Addendum.
            </p>
          </Section>

          <Section title="Content you upload">
            <p>
              Your files may contain personal data about you or other people.
              You are responsible for making sure you are allowed to upload
              them. Please do not upload special category data (such as health
              or biometric data), criminal records, payment card details or
              passwords. Our{" "}
              <Link href="/terms" className="underline hover:text-foreground">
                terms of use
              </Link>{" "}
              explain this further.
            </p>
          </Section>

          <Section title="How long we keep it">
            <p>
              We keep your files, conversations and account details until you
              delete them or close your account. After that we remove them from
              our systems within 30 days, except where we must keep something to
              meet a legal obligation. Backups may hold copies for a short time
              longer.
            </p>
          </Section>

          <Section title="Security">
            <p>
              We use appropriate technical and organisational measures to
              protect your data, including encryption in transit and for stored
              files, and access controls limited to what is needed to run the
              service. No system is completely secure, so please keep your
              password confidential and think carefully about what you upload.
            </p>
            <p>
              If a personal data breach occurs that we are required to report,
              we will notify the Information Commissioner&apos;s Office and
              affected users as the law requires. Our responsibility to you is
              set out in our terms of use.
            </p>
          </Section>

          <Section title="Cookies">
            <p>
              We only use cookies or similar storage that are needed to keep you
              signed in and the service working. We do not use advertising or
              tracking cookies.
            </p>
          </Section>

          <Section title="Your rights">
            <p>
              You can ask us to access, correct, delete or export your personal
              data, to restrict how we use it, or to object to our use of it.
              Email 101akhere5@gmail.com and we will respond within one month.
              You can also delete files and conversations yourself in the app.
            </p>
            <p>
              If you are unhappy with how we handle your data, we would like the
              chance to put it right first. You can also complain to the
              Information Commissioner&apos;s Office at ico.org.uk.
            </p>
          </Section>

          <Section title="Children">
            <p>
              The service is not intended for anyone under 18, and we do not
              knowingly collect their data.
            </p>
          </Section>

          <Section title="Changes to this policy">
            <p>
              If we make significant changes, we will update the date above and
              let you know in the app or by email before they take effect.
            </p>
          </Section>
        </div>

        <p className="mt-12 text-sm text-muted-foreground">
          See also our{" "}
          <Link href="/terms" className="underline hover:text-foreground">
            terms of use
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
