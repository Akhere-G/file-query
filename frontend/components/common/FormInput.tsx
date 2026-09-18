import { InputHTMLAttributes } from "react";
import { Field, FieldDescription, FieldLabel } from "../ui/field";
import { Input } from "../ui/input";

interface FormInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  description?: string;
}
export default function FormInput({
  label,
  description,
  className,
  ...rest
}: FormInputProps) {
  return (
    <Field className="gap-0">
      <FieldLabel>{label}</FieldLabel>
      <Input {...rest} className={`mb-2 ${className}`} />
      <FieldDescription className="text-xs h-4 text-destructive">
        {description}
      </FieldDescription>
    </Field>
  );
}
