import { TopNavbar } from "@/components/TopNavbar";
import { MapDashboard } from "@/components/MapDashboard";

const Index = () => {
  return (
    <div className="h-screen w-screen overflow-hidden bg-background relative flex flex-col">
      <TopNavbar active="home" />
      <div className="flex-1 relative overflow-hidden">
        <MapDashboard />
      </div>
    </div>
  );
};

export default Index;
