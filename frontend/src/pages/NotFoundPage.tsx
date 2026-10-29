import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { EmptyState } from "@/components/common";
import { Button } from "@/components/ui/button";
import { useDocumentTitle } from "@/hooks/useTheme";

export default function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <div className="container py-20">
      <EmptyState icon={Compass} title="Page not found" description="The page you were looking for doesn't exist or has moved."
        action={<Button asChild><Link to="/">Back to home</Link></Button>} />
    </div>
  );
}
