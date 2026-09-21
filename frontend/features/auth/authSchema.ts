import * as z from "zod";

export const Password = z
  .string()
  .min(1, { error: "Password is required" })
  .superRefine((val, ctx) => {
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

export const registerSchema = z
  .object({
    email: z.email().trim().min(1, { error: "Email is required" }).max(255),
    username: z
      .string()
      .trim()
      .min(1, { error: "Username is required" })
      .max(255),
    password: Password,
    repeatPassword: z.string(),
  })
  .refine((data) => data.password === data.repeatPassword, {
    path: ["repeatPassword"],
    message: "Passwords must match",
  });

export type LoginSchema = z.infer<typeof loginSchema>;
export type RegisterSchema = z.infer<typeof registerSchema>;
