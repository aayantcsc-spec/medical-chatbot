import { Layers, Stethoscope } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/common";
import { Alert } from "@/components/ui/primitives";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/overlays";
import { useDocumentTitle } from "@/hooks/useTheme";
import { HealthQaCompare, useTopics } from "@/features/health-qa/HealthQaCompare";
import { SymptomComparison } from "./SymptomComparison";

export default function ChatbotComparisonPage({ fixedMode }: { fixedMode?: "symptom" }) {
  useDocumentTitle(fixedMode ? "Six-Architecture Comparison" : "Chatbot Comparison");
  const [params, setParams] = useSearchParams();
  const mode = fixedMode ?? (params.get("mode") === "health_qa" ? "health_qa" : "symptom");
  const topics = useTopics();

  return (
    <>
      <PageHeader eyebrow="Live comparison" title="Compare Healthcare AI Models"
        description="Submit the same question to different chatbot architectures and explore their responses, speed, evidence, and limitations." />
      <Alert variant="info" className="mb-5">
        This page compares live replies to <em>your</em> question. To measure performance across a test dataset, use Model Evaluation.
        No model is labelled medically superior from speed or keyword matching.
      </Alert>
      {fixedMode ? <SymptomComparison /> : (
        <Tabs value={mode} onValueChange={(v) => setParams(v === "symptom" ? {} : { mode: v }, { replace: true })}>
          <TabsList aria-label="Comparison mode">
            <TabsTrigger value="symptom"><Layers /> Mode A · Six architectures</TabsTrigger>
            <TabsTrigger value="health_qa"><Stethoscope /> Mode B · Health Q&amp;A bots</TabsTrigger>
          </TabsList>
          <TabsContent value="symptom"><SymptomComparison /></TabsContent>
          <TabsContent value="health_qa"><HealthQaCompare topics={topics.data} /></TabsContent>
        </Tabs>
      )}
    </>
  );
}
