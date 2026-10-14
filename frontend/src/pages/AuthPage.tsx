import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Logo } from "../components/Logo";
import { useAuth } from "../hooks/useAuth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
const registerSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z
    .string()
    .min(8, "Use at least 8 characters")
    .max(72, "Use at most 72 characters")
    .refine((v) => /[A-Za-z]/.test(v) && /[^A-Za-z]/.test(v), "Mix letters with numbers or symbols"),
});

type Values = z.infer<typeof loginSchema>;

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { token, login, register: signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(mode === "login" ? loginSchema : registerSchema) });

  if (token) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from ?? (mode === "register" ? "/app/resume" : "/app")} replace />;
  }

  async function submit(values: Values) {
    setServerError(null);
    try {
      if (mode === "login") await login(values.email, values.password);
      else await signUp(values.email, values.password);
      navigate(mode === "register" ? "/app/resume" : "/app", { replace: true });
    } catch (e) {
      setServerError(e instanceof Error ? e.message : "Something went wrong.");
    }
  }

  const isLogin = mode === "login";
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-4 py-10">
      <Link to="/" className="mb-8 no-underline">
        <Logo />
      </Link>
      <div className="panel w-full max-w-sm p-6">
        <h1 className="text-xl font-bold">{isLogin ? "Sign in" : "Create your account"}</h1>
        {!isLogin && <p className="mt-1 text-sm text-muted">You'll upload your resume next.</p>}
        <form onSubmit={handleSubmit(submit)} className="mt-6 space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="field-label">
              Email
            </label>
            <input id="email" type="email" autoComplete="email" className="field-input" aria-invalid={Boolean(errors.email)} {...register("email")} />
            {errors.email && <p className="mt-1 text-sm text-danger">{errors.email.message}</p>}
          </div>
          <div>
            <label htmlFor="password" className="field-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
              className="field-input"
              aria-invalid={Boolean(errors.password)}
              {...register("password")}
            />
            {errors.password ? (
              <p className="mt-1 text-sm text-danger">{errors.password.message}</p>
            ) : (
              !isLogin && <p className="mt-1 text-sm text-muted">At least 8 characters, mixing letters with numbers or symbols.</p>
            )}
          </div>
          {serverError && (
            <p role="alert" className="text-sm text-danger">
              {serverError}
            </p>
          )}
          <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-sm text-muted">
          {isLogin ? (
            <>
              New here? <Link to="/register">Create an account</Link>
            </>
          ) : (
            <>
              Already have an account? <Link to="/login">Sign in</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
