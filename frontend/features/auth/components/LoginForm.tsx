"use client";
import { useState } from "react";
import { login } from "../api/authApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoginSchema, loginSchema } from "../authSchema";
import FormInput from "@/components/common/FormInput";
import { getErrorMessage } from "@/lib/apiUtils";

export default function LoginForm() {
  const [isPending, setIsPending] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { handleSubmit, register, setError, formState } = useForm<LoginSchema>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginSchema) {
    if (isPending) return;
    setIsPending(true);
    setFormError(null);

    try {
      const result = await login(data.email, data.password);
      if (!result.success) {
        const unmatchedMessages: string[] = [];

        if (result.details) {
          for (const [field, messages] of Object.entries(result.details)) {
            if (field === "email" || field === "password") {
              setError(field, {
                type: "server",
                message: messages.join(" "),
              });
            } else {
              unmatchedMessages.push(...messages);
            }
          }
        }

        setFormError(result.message ?? (unmatchedMessages.join(" ") || null));
      }
    } catch {
      setFormError(getErrorMessage(null));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card>
      <CardContent>
        <form className="form" onSubmit={handleSubmit(onSubmit)}>
          <h2 className="title">Log in</h2>
          {formError && <p role="alert">{formError}</p>}
          <FormInput
            label="Email"
            id="email"
            placeholder="Email"
            {...register("email")}
            description={formState.errors.email?.message}
          />
          <FormInput
            label="Password"
            id="password"
            type="password"
            {...register("password")}
            description={formState.errors.password?.message}
          />
          <Button type="submit">Login</Button>
        </form>
      </CardContent>
    </Card>
  );
}
