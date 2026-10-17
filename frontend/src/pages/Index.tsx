import { TopNavbar } from "@/components/TopNavbar";
import { MapDashboard } from "@/components/MapDashboard";
import { MapTour } from "@/components/MapTour";

const Index = () => {
  return (
    <div className="h-screen w-screen overflow-hidden bg-background relative flex flex-col">
      <TopNavbar active="home" />
      <div className="flex-1 relative overflow-hidden">
        <MapDashboard />
      </div>
      {/* First-visit guide for public visitors (also "Take the tour" in the menu). */}
      <MapTour />
    </div>
  );
};

export default Index;
