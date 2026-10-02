import { Suspense } from "react";

import { AuthForm } from "../auth-form";

export default function Page() {
  return (
    <Suspense>
      <AuthForm mode="signup" />
    </Suspense>
  );
}
