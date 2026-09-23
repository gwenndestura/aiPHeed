import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth";
import { RequireAdmin } from "@/components/RequireAdmin";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import Login from "./pages/Login.tsx";
import Admin from "./pages/Admin.tsx";
import DataPage from "./pages/Data.tsx";
import VisualizationPage from "./pages/Visualization.tsx";
import Landing from "./pages/Landing.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Index />} />
            <Route path="/data" element={<DataPage />} />
            <Route path="/visualization" element={<VisualizationPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/admin" element={<RequireAdmin><Admin /></RequireAdmin>} />
            <Route path="/admin/feedback" element={<RequireAdmin><Admin initialSection="feedback" /></RequireAdmin>} />
            <Route path="/admin/review" element={<RequireAdmin><Admin initialSection="review" /></RequireAdmin>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
