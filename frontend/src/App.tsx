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
import E25Timeline from "./pages/E25Timeline.tsx";
import E27Timeline from "./pages/E27Timeline.tsx";
import E28Brief from "./pages/E28Brief.tsx";
import E29Brief from "./pages/E29Brief.tsx";
import E31Brief from "./pages/E31Brief.tsx";
import NewsEvidence from "./pages/NewsEvidence.tsx";

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
            <Route path="/forecast-timeline" element={<E27Timeline />} />
            <Route path="/forecast-timeline/e25" element={<E25Timeline />} />
            <Route path="/da-brief" element={<E31Brief />} />
            <Route path="/news" element={<NewsEvidence />} />
            <Route path="/da-brief/e29" element={<E29Brief />} />
            <Route path="/da-brief/e28" element={<E28Brief />} />
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
