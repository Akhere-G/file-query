"use client";

import { register as registerFn } from "../api/authApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { RegisterSchema, registerSchema } from "../authSchema";
import FormInput from "@/components/common/FormInput";
import { getErrorMessage } from "@/lib/apiUtils";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function RegisterForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const router = useRouter();
  const { handleSubmit, register, setError, formState } =
    useForm<RegisterSchema>({
      resolver: zodResolver(registerSchema),
    });

  async function onSubmit(data: RegisterSchema) {
    setFormError(null);

    try {
      const result = await registerFn(data.email, data.password, data.username);

      if (!result.success) {
        const unmatchedMessages: string[] = [];

        if (result.details) {
          for (const [field, messages] of Object.entries(result.details)) {
            if (
              field === "email" ||
              field === "password" ||
              field === "username" ||
              field === "repeatPassword"
            ) {
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
      } else {
        router.push("/dashboard");
      }
    } catch (error) {
      setFormError(getErrorMessage(error));
    }
  }

  return (
    <Card>
      <CardContent>
        <form className="form" onSubmit={handleSubmit(onSubmit)}>
          <h2 className="title">Register</h2>

          {formError && <p role="alert">{formError}</p>}

          <FormInput
            label="Username"
            id="username"
            {...register("username")}
            description={formState.errors.username?.message}
          />

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

          <FormInput
            label="Repeat Password"
            id="repeatPassword"
            type="password"
            {...register("repeatPassword")}
            description={formState.errors.repeatPassword?.message}
          />

          <Button type="submit" disabled={formState.isSubmitting}>
            {formState.isSubmitting ? "Registering..." : "Register"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
