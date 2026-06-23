import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "@/components/AppShell"
import { EmployeeShell } from "@/components/EmployeeShell"
import { MarketingShell } from "@/components/marketing/MarketingShell"
import {
  AdminRoute,
  CustomerPublicRoute,
  CustomerRoute,
  EmployeePublicRoute,
  EmployeeRoute,
  PublicOnlyRoute,
} from "@/components/ProtectedRoute"
import { Customers } from "@/pages/Customers"
import { Dashboard } from "@/pages/Dashboard"
import { Enrollment } from "@/pages/Enrollment"
import { Recognition } from "@/pages/Recognition"
import { Identities } from "@/pages/Identities"
import { Employees } from "@/pages/Employees"
import { Logs } from "@/pages/Logs"
import { AdminSettingsPage } from "@/pages/AdminSettingsPage"
import { Login } from "@/pages/Login"
import { Signup } from "@/pages/Signup"
import { AuthKiosk } from "@/pages/AuthKiosk"
import { EmployeeLogin } from "@/pages/employee/EmployeeLogin"
import { EmployeeSignup } from "@/pages/employee/EmployeeSignup"
import { EmployeeDashboardPage } from "@/pages/employee/EmployeeDashboardPage"
import { EmployeeAttendancePage } from "@/pages/employee/EmployeeAttendancePage"
import { EmployeeActivityPage } from "@/pages/employee/EmployeeActivityPage"
import { EmployeeSettingsPage } from "@/pages/employee/EmployeeSettingsPage"
import { ContactPage } from "@/pages/marketing/ContactPage"
import { FaqRedirect } from "@/pages/marketing/FaqRedirect"
import { HomePage } from "@/pages/marketing/HomePage"
import { HowItWorksPage } from "@/pages/marketing/HowItWorksPage"
import { SecurityPage } from "@/pages/marketing/SecurityPage"
import { SolutionsPage } from "@/pages/marketing/SolutionsPage"
import { TechnologyPage } from "@/pages/marketing/TechnologyPage"
import { UserEnrollPage } from "@/pages/user/UserEnrollPage"
import { UserLogin } from "@/pages/user/UserLogin"
import { UserScanPage } from "@/pages/user/UserScanPage"
import { UserSignup } from "@/pages/user/UserSignup"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MarketingShell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/technology" element={<TechnologyPage />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />
          <Route path="/security" element={<SecurityPage />} />
          <Route path="/solutions" element={<SolutionsPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/faq" element={<FaqRedirect />} />
          <Route
            path="/member/enrollment"
            element={
              <CustomerRoute>
                <UserEnrollPage />
              </CustomerRoute>
            }
          />
          <Route
            path="/member/recognition"
            element={
              <CustomerRoute>
                <UserScanPage />
              </CustomerRoute>
            }
          />
        </Route>

        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <Login />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicOnlyRoute>
              <Signup />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/employee/login"
          element={
            <EmployeePublicRoute>
              <EmployeeLogin />
            </EmployeePublicRoute>
          }
        />
        <Route
          path="/employee/signup"
          element={
            <EmployeePublicRoute>
              <EmployeeSignup />
            </EmployeePublicRoute>
          }
        />
        <Route
          path="/user/login"
          element={
            <CustomerPublicRoute>
              <UserLogin />
            </CustomerPublicRoute>
          }
        />
        <Route
          path="/user/signup"
          element={
            <CustomerPublicRoute>
              <UserSignup />
            </CustomerPublicRoute>
          }
        />
        <Route path="/kiosk" element={<AuthKiosk />} />

        <Route
          element={
            <AdminRoute>
              <AppShell />
            </AdminRoute>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/enroll" element={<Enrollment />} />
          <Route path="/recognize" element={<Recognition />} />
          <Route path="/identities" element={<Identities />} />
          <Route path="/employees" element={<Employees />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<AdminSettingsPage />} />
        </Route>

        <Route
          element={
            <EmployeeRoute>
              <EmployeeShell />
            </EmployeeRoute>
          }
        >
          <Route path="/employee/dashboard" element={<EmployeeDashboardPage />} />
          <Route path="/employee/attendance" element={<EmployeeAttendancePage />} />
          <Route path="/employee/activity" element={<EmployeeActivityPage />} />
          <Route path="/employee/settings" element={<EmployeeSettingsPage />} />
          <Route path="/employee/profile" element={<Navigate to="/employee/settings" replace />} />
          <Route path="/employee/scan" element={<Navigate to="/employee/dashboard" replace />} />
        </Route>

        <Route path="/user/dashboard" element={<Navigate to="/" replace />} />
        <Route path="/user/enroll" element={<Navigate to="/member/enrollment" replace />} />
        <Route path="/user/scan" element={<Navigate to="/member/recognition" replace />} />
        <Route path="/user/*" element={<Navigate to="/" replace />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
