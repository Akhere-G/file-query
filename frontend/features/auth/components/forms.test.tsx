import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const login = vi.fn();
const register = vi.fn();
const startDemo = vi.fn();
const track = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("../api/authApi", () => ({
  login: (...args: unknown[]) => login(...args),
  register: (...args: unknown[]) => register(...args),
  startDemo: (...args: unknown[]) => startDemo(...args),
}));
vi.mock("@/lib/analytics/client", () => ({ track: (...args: unknown[]) => track(...args) }));

import DemoButton from "./DemoButton";
import LoginForm from "./LoginForm";
import RegisterForm from "./RegisterForm";

const failure = (overrides: object = {}) => ({
  success: false,
  message: null,
  details: null,
  status: 400,
  ...overrides,
});

beforeEach(() => [push, login, register, startDemo, track].forEach((m) => m.mockReset()));

describe("LoginForm", () => {
  const fill = async (user: ReturnType<typeof userEvent.setup>, email: string, password: string) => {
    if (email) await user.type(screen.getByPlaceholderText("Email"), email);
    if (password) await user.type(document.querySelector("#password")!, password);
    await user.click(screen.getByRole("button", { name: "Login" }));
  };

  it("signs in and goes to the dashboard", async () => {
    login.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    render(<LoginForm />);

    await fill(user, "ada@example.com", "Passw0rdTest");

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(login).toHaveBeenCalledWith("ada@example.com", "Passw0rdTest");
  });

  it("validates before calling the server", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await fill(user, "not-an-email", "");

    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it("shows the server's message for bad credentials and stays on the page", async () => {
    login.mockResolvedValue(failure({ message: "Invalid credentials.", status: 401 }));
    const user = userEvent.setup();
    render(<LoginForm />);

    await fill(user, "ada@example.com", "Passw0rdTest");

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials.");
    expect(push).not.toHaveBeenCalled();
    expect(track).toHaveBeenCalledWith("login_failed", { reason: "unauthorised" });
  });

  it("attaches server validation errors to their fields", async () => {
    login.mockResolvedValue(failure({ details: { email: ["Value is not a valid email address."] } }));
    const user = userEvent.setup();
    render(<LoginForm />);

    await fill(user, "ada@example.com", "Passw0rdTest");

    expect(await screen.findByText("Value is not a valid email address.")).toBeInTheDocument();
  });

  it("disables the button while signing in", async () => {
    let finish!: (value: unknown) => void;
    login.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const user = userEvent.setup();
    render(<LoginForm />);

    await fill(user, "ada@example.com", "Passw0rdTest");

    expect(await screen.findByRole("button", { name: "Logging in..." })).toBeDisabled();
    finish({ success: true });
  });

  it("offers the demo", () => {
    render(<LoginForm />);

    expect(screen.getByRole("button", { name: "Just looking? Try the demo" })).toBeInTheDocument();
  });
});

describe("RegisterForm", () => {
  async function fillValid(user: ReturnType<typeof userEvent.setup>, overrides: Record<string, string> = {}) {
    const values = {
      username: "Ada",
      email: "ada@example.com",
      password: "Passw0rdTest",
      repeatPassword: "Passw0rdTest",
      ...overrides,
    };
    for (const [id, value] of Object.entries(values)) {
      await user.type(document.querySelector(`#${id}`)!, value);
    }
  }

  it("registers a new user and goes to the dashboard", async () => {
    register.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    render(<RegisterForm />);

    await fillValid(user);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(register).toHaveBeenCalledWith("ada@example.com", "Passw0rdTest", "Ada");
  });

  it("requires the terms to be accepted", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    await fillValid(user);
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByText("You must accept the terms and conditions to register")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it.each([
    ["weakpassword", /at least 1 number/],
    ["weakpass1", /at least 1 uppercase/],
    ["WEAKPASS1", /at least 1 lowercase/],
  ])("rejects the password %s before calling the server", async (password, message) => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    await fillValid(user, { password, repeatPassword: password });
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("flags passwords that do not match", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    await fillValid(user, { repeatPassword: "Different1" });
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByText("Passwords must match")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("tells the user when the email is already registered", async () => {
    register.mockResolvedValue(failure({ message: "That already exists", status: 409 }));
    const user = userEvent.setup();
    render(<RegisterForm />);

    await fillValid(user);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("That already exists");
    expect(push).not.toHaveBeenCalled();
    expect(track).toHaveBeenCalledWith("register_failed", { reason: "conflict" });
  });
});

describe("DemoButton", () => {
  it("starts the demo and goes to the dashboard", async () => {
    startDemo.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    render(<DemoButton />);

    await user.click(screen.getByRole("button", { name: "Try demo" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows why the demo could not start", async () => {
    startDemo.mockResolvedValue(failure({ message: "The demo is not available right now.", status: 503 }));
    const user = userEvent.setup();
    render(<DemoButton />);

    await user.click(screen.getByRole("button", { name: "Try demo" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The demo is not available right now.");
    expect(push).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Try demo" })).toBeEnabled();
  });
});
