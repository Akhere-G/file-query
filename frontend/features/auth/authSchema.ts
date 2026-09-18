import * as z from "zod";

export const Password = z.string().superRefine((val, ctx) => {
  if (!/[0-9]/.test(val)) {
    ctx.addIssue({
      code: "custom",
      message: "Password must include at least 1 number.",
      input: val,
    });
  }

  if (!/[a-z]/.test(val)) {
    ctx.addIssue({
      code: "custom",
      message: "Password must include at least 1 lowercase letter.",
      input: val,
    });
  }

  if (!/[A-Z]/.test(val)) {
    ctx.addIssue({
      code: "custom",
      message: "Password must include at least 1 uppercase letter.",
      input: val,
    });
  }
});

export const loginSchema = z.object({
  email: z.email().trim().min(1, { error: "Email is required" }),
  password: z.string().trim().min(1, { error: "Password is required" }),
});

export type LoginSchema = z.infer<typeof loginSchema>;
