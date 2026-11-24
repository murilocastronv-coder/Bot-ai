import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import Landing from "./pages/Landing";
import { Forgot, Login, Register, Reset } from "./pages/Auth";
import { Privacy, Terms } from "./pages/Legal";
import { Loading } from "./components/ui";

const AppLayout = lazy(() => import("./components/AppLayout"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Agent = lazy(() => import("./pages/Agent"));
const Channels = lazy(() => import("./pages/Channels"));
const Billing = lazy(() => import("./pages/Billing"));
const Account = lazy(() => import("./pages/Account"));
const Admin = lazy(() => import("./pages/Admin"));
const Conversations = lazy(() => import("./pages/Conversations").then((m) => ({ default: m.Conversations })));
const ConversationDetail = lazy(() => import("./pages/Conversations").then((m) => ({ default: m.ConversationDetail })));
const Contacts = lazy(() => import("./pages/Crm").then((m) => ({ default: m.Contacts })));
const Calendar = lazy(() => import("./pages/Crm").then((m) => ({ default: m.Calendar })));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot" element={<Forgot />} />
          <Route path="/reset" element={<Reset />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="conversations" element={<Conversations />} />
            <Route path="conversations/:id" element={<ConversationDetail />} />
            <Route path="contacts" element={<Contacts />} />
            <Route path="calendar" element={<Calendar />} />
            <Route path="agent" element={<Agent />} />
            <Route path="channels" element={<Channels />} />
            <Route path="billing" element={<Billing />} />
            <Route path="account" element={<Account />} />
            <Route path="admin" element={<Admin />} />
          </Route>
          <Route path="*" element={<Landing />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  </React.StrictMode>,
);
