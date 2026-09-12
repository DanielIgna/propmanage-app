// ServiceGate — REGULA PLATFORMEI: rutele serviciilor dezactivate nu sunt accesibile public.
// Adminii păstrează acces intern (dezvoltare); reactivarea se face din Admin → Menu Manager.
import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useServiceVisibility, isServiceEnabled } from "./serviceVisibility";

export const ServiceGate = ({ serviceId, children }) => {
  const { user } = useAuth();
  const services = useServiceVisibility();
  // user === null → auth încă se verifică; așteptăm ca adminii să nu fie redirecționați greșit
  if (user === null || services === null) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center" data-testid="service-gate-loading">
        <div className="w-6 h-6 border-2 border-stone-600 border-t-[#d4ff3a] rounded-full animate-spin" />
      </div>
    );
  }
  if (user && user.role === "admin") return children;
  if (!isServiceEnabled(services, serviceId)) return <Navigate to="/" replace />;
  return children;
};
