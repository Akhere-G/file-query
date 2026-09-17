import Link from "next/link";

export default function Custom404() {
  return (
    <div className="container flex flex-col gap-4">
      <h2 className="title">Page not found</h2>
      <Link href="/">Return home?</Link>
    </div>
  );
}
