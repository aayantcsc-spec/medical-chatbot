import { forwardRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Info } from "lucide-react";
import { TextLink } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, FieldError, Input, Label } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useTheme";
import { ApiError } from "@/lib/api";
import { AuthShell } from "@/layouts/PublicLayout";

const loginSchema = z.object({
  email: z.string().trim().min(1, "Enter your email").email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
const registerSchema = z.object({
  name: z.string().trim().min(1, "Enter your name").max(80, "At most 80 characters"),
  email: z.string().trim().min(1, "Enter your email").email("Enter a valid email address"),
  password: z.string().min(8, "At least 8 characters").max(128).regex(/[A-Za-z]/, "Include a letter").regex(/\d/, "Include a number"),
});

// forwardRef is required: react-hook-form's register() reads the value through the input's ref.
const PasswordInput = forwardRef<HTMLInputElement, React.ComponentProps<typeof Input>>(function PasswordInput(props, ref) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input {...props} ref={ref} type={show ? "text" : "password"} className="pr-10" />
      <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"}
        className="absolute inset-y-0 right-0 grid w-10 place-items-center text-muted-foreground hover:text-foreground">
        {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  );
});

export function LoginPage() {
  useDocumentTitle("Sign in");
  const { login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from;
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    try {
      const user = await login(v.email, v.password);
      navigate(user.onboarded ? from || "/dashboard" : "/onboarding", { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sign-in failed. Please try again.");
    }
  });

  return (
    <AuthShell title="Welcome back" subtitle={<>New here? <TextLink to="/register">Create an account</TextLink></>}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && <Alert variant="critical">{error}</Alert>}
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} aria-describedby="email-err" {...register("email")} />
          <FieldError id="email-err">{errors.email?.message}</FieldError>
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs font-medium text-primary hover:underline">Forgot password?</Link>
          </div>
          <PasswordInput id="password" autoComplete="current-password" aria-invalid={!!errors.password} aria-describedby="pw-err" {...register("password")} />
          <FieldError id="pw-err">{errors.password?.message}</FieldError>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>Sign in</Button>
      </form>
    </AuthShell>
  );
}

export function RegisterPage() {
  useDocumentTitle("Create account");
  const { register: signup } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, setError: setFieldError, formState: { errors, isSubmitting } } =
    useForm<z.infer<typeof registerSchema>>({ resolver: zodResolver(registerSchema) });

  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    try {
      await signup(v.name, v.email, v.password);
      navigate("/onboarding", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.field && ["name", "email", "password"].includes(e.field)) {
        setFieldError(e.field as "name" | "email" | "password", { message: e.message });
      } else {
        setError(e instanceof ApiError ? e.message : "Registration failed. Please try again.");
      }
    }
  });

  return (
    <AuthShell title="Create your account" subtitle={<>Already registered? <TextLink to="/login">Sign in</TextLink></>}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && <Alert variant="critical">{error}</Alert>}
        <div className="space-y-1.5">
          <Label htmlFor="name">Name</Label>
          <Input id="name" autoComplete="name" aria-invalid={!!errors.name} aria-describedby="name-err" {...register("name")} />
          <FieldError id="name-err">{errors.name?.message}</FieldError>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} aria-describedby="email-err" {...register("email")} />
          <FieldError id="email-err">{errors.email?.message}</FieldError>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <PasswordInput id="password" autoComplete="new-password" aria-invalid={!!errors.password} aria-describedby="pw-hint pw-err" {...register("password")} />
          <p id="pw-hint" className="text-xs text-muted-foreground">At least 8 characters, with a letter and a number.</p>
          <FieldError id="pw-err">{errors.password?.message}</FieldError>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>Create account</Button>
        <p className="text-center text-xs text-muted-foreground">We only ask for what is needed to sign you in. Your password is stored as a salted hash.</p>
      </form>
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  useDocumentTitle("Password recovery");
  return (
    <AuthShell title="Password recovery" subtitle="Reset by email is not available in this local research build">
      <div className="space-y-4">
        <Alert variant="info" title="No email service is configured">
          This installation runs locally without an email server, so a reset link cannot be sent - and we will not pretend to send one.
        </Alert>
        <div className="flex gap-2 text-sm text-muted-foreground">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          <p>Ask the person running this MediChat instance to help, or create a new account. Your old conversations stay with the old account.</p>
        </div>
        <Button variant="outline" className="w-full" asChild><Link to="/login">Back to sign in</Link></Button>
      </div>
    </AuthShell>
  );
}
