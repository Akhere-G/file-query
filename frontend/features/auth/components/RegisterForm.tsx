"use client";

import { register as registerFn } from "../api/authApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { RegisterSchema, registerSchema } from "../authSchema";
import FormInput from "@/components/common/FormInput";
import { getErrorMessage } from "@/lib/apiUtils";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [termsError, setTermsError] = useState<string | null>(null);
  const router = useRouter();
  const { handleSubmit, register, setError, formState } =
    useForm<RegisterSchema>({
      resolver: zodResolver(registerSchema),
    });

  async function onSubmit(data: RegisterSchema) {
    setFormError(null);
    setTermsError(null);

    if (!termsAccepted) {
      setTermsError("You must accept the terms and conditions to register");
      return;
    }

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

          <div className="-mt-2 flex items-start gap-2">
            <Checkbox
              id="termsAccepted"
              checked={termsAccepted}
              onCheckedChange={(checked) => {
                setTermsAccepted(checked);
                setTermsError(null);
              }}
            />
            <Label
              htmlFor="termsAccepted"
              className="flex-1 cursor-pointer text-sm font-normal normal-case"
            >
              I agree to the{" "}
              <Link href="/terms" className="underline hover:text-foreground">
                Terms of Use
              </Link>{" "}
              and{" "}
              <Link href="/privacy" className="underline hover:text-foreground">
                Privacy Policy
              </Link>
            </Label>
          </div>

          {termsError && (
            <p className="text-sm text-destructive" role="alert">
              {termsError}
            </p>
          )}
          <Link className="mt-2" href="/login">
            Already have an account?
          </Link>

          <Button type="submit" disabled={formState.isSubmitting}>
            {formState.isSubmitting ? "Registering..." : "Register"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
