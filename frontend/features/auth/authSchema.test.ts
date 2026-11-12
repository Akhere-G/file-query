import { describe, expect, it } from "vitest";

import { loginSchema, Password, registerSchema } from "./authSchema";

const validRegistration = {
  email: "ada@example.com",
  username: "Ada",
  password: "Passw0rdTest",
  repeatPassword: "Passw0rdTest",
};

const messages = (result: { success: boolean; error?: { issues: { message: string }[] } }) =>
  result.error?.issues.map((issue) => issue.message) ?? [];

describe("Password", () => {
  it("accepts a password with a digit, lowercase and uppercase letter", () => {
    expect(Password.safeParse("Passw0rdTest").success).toBe(true);
  });

  it.each([
    ["Password1".toUpperCase(), "lowercase"],
    ["password1", "uppercase"],
    ["PasswordNoDigit", "number"],
  ])("rejects %s because it lacks a %s", (password, missing) => {
    const result = Password.safeParse(password);

    expect(result.success).toBe(false);
    expect(messages(result).join(" ")).toContain(missing);
  });

  it("reports every missing requirement at once", () => {
    expect(messages(Password.safeParse("!!!!"))).toHaveLength(3);
  });

  it("requires a value and caps the length at 128", () => {
    expect(Password.safeParse("").success).toBe(false);
    expect(Password.safeParse("Aa1" + "x".repeat(125)).success).toBe(true);
    expect(Password.safeParse("Aa1" + "x".repeat(126)).success).toBe(false);
  });
});

describe("registerSchema", () => {
  it("accepts a valid registration", () => {
    expect(registerSchema.safeParse(validRegistration).success).toBe(true);
  });

  it("flags mismatching passwords on the repeat field", () => {
    const result = registerSchema.safeParse({ ...validRegistration, repeatPassword: "Different1" });

    expect(result.success).toBe(false);
    expect(result.error?.issues[0]).toMatchObject({
      path: ["repeatPassword"],
      message: "Passwords must match",
    });
  });

  it.each(["not-an-email", "a@", ""])("rejects the email %j", (email) => {
    expect(registerSchema.safeParse({ ...validRegistration, email }).success).toBe(false);
  });

  it("requires a non-blank username", () => {
    expect(registerSchema.safeParse({ ...validRegistration, username: "   " }).success).toBe(false);
  });

  it("trims the username", () => {
    const result = registerSchema.safeParse({ ...validRegistration, username: "  Ada  " });

    expect(result.data?.username).toBe("Ada");
  });
});

describe("loginSchema", () => {
  it("requires an email and a password", () => {
    expect(loginSchema.safeParse({ email: "a@b.co", password: "x" }).success).toBe(true);
    expect(loginSchema.safeParse({ email: "a@b.co", password: "  " }).success).toBe(false);
    expect(loginSchema.safeParse({ email: "nope", password: "x" }).success).toBe(false);
  });
});
