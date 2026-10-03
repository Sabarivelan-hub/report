import React, { useState, useEffect } from 'react';
import {
  FileText,
  Database,
  Bot,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Download,
  Search,
  Code,
  ArrowRight,
  ShieldCheck,
  ChevronRight,
  BookOpen,
  Clock,
  Activity,
  Cpu,
  UploadCloud,
  FileCheck,
  HelpCircle,
  Copy,
  ExternalLink,
  ChevronDown,
  Eye
} from 'lucide-react';

interface Template {
  id: string;
  name: string;
  description: string;
  report_type: string;
  template_structure: any;
}

interface RefDoc {
  id: string;
  title: string;
  file_name: string;
  document_type: string;
  metadata: any;
  chunk_count?: number;
  created_at: string;
}

interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  document_title: string;
  similarity_score?: number;
}

interface GenerationLog {
  id: string;
  agent_name: string;
  input_data: any;
  output_data: any;
  execution_time: number;
  status: string;
  created_at: string;
}

interface ReportVersion {
  id: string;
  version_number: number;
  content: any;
  validation_result: any;
  created_at: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'studio' | 'rag' | 'schema' | 'logs' | 'code'>('studio');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [documents, setDocuments] = useState<RefDoc[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  
  // Studio Inputs
  const [userInput, setUserInput] = useState<string>(
    'Create an industrial visit report for ABC Technologies.\nThe visit happened on 25 September 2026.\n52 IT students attended.\nTopics included AI, Cloud Computing and DevOps.'
  );
  
  // Pipeline State
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [pipelineReport, setPipelineReport] = useState<any>(null);
  const [selectedVersion, setSelectedVersion] = useState<number>(1);
  const [activeLogAgent, setActiveLogAgent] = useState<string | null>(null);

  // RAG Query State
  const [searchQuery, setSearchQuery] = useState('cloud native microservices and CI/CD pipelines');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedDocChunks, setSelectedDocChunks] = useState<DocumentChunk[]>([]);
  const [viewingDocTitle, setViewingDocTitle] = useState<string>('');

  // Code Explorer State
  const [codeTree, setCodeTree] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('app/agents/input_analyzer.py');
  const [fileContent, setFileContent] = useState<string>('');
  const [loadingCode, setLoadingCode] = useState(false);

  // New Document Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [newDocTitle, setNewDocTitle] = useState('');
  const [newDocType, setNewDocType] = useState('industrial_visit');
  const [newDocDept, setNewDocDept] = useState('Computer Science');
  const [newDocContent, setNewDocContent] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);

  // Load initial templates, docs, and code tree
  useEffect(() => {
    fetchTemplates();
    fetchDocuments();
    fetchCodeFiles();
  }, []);

  const fetchTemplates = async () => {
    try {
      const res = await fetch('/api/v1/templates');
      const data = await res.json();
      setTemplates(data);
      if (data.length > 0) setSelectedTemplateId(data[0].id);
    } catch (err) {
      console.error('Error fetching templates', err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/v1/documents');
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      console.error('Error fetching documents', err);
    }
  };

  const fetchCodeFiles = async () => {
    try {
      const res = await fetch('/api/v1/code-files');
      const data = await res.json();
      setCodeTree(data);
      if (data.length > 0 && data[0].files.length > 0) {
        loadFileContent(data[0].files[0].path);
      }
    } catch (err) {
      console.error('Error fetching code files', err);
    }
  };

  const loadFileContent = async (filePath: string) => {
    setSelectedFile(filePath);
    setLoadingCode(true);
    try {
      const res = await fetch(`/api/v1/code-content?path=${encodeURIComponent(filePath)}`);
      const data = await res.json();
      setFileContent(data.content || 'File empty or not found');
    } catch (err) {
      setFileContent('Error loading source code file');
    } finally {
      setLoadingCode(false);
    }
  };

  // Launch Full Multi-Agent Pipeline
  const handleGenerateReport = async () => {
    if (!userInput.trim()) return;
    setIsGenerating(true);
    setCurrentStep(1); // Agent 1: Input Analysis
    setPipelineReport(null);

    // Simulate animated step progression for UI visual feedback while API runs
    const stepTimer = setInterval(() => {
      setCurrentStep(prev => (prev < 4 ? prev + 1 : prev));
    }, 1800);

    try {
      const res = await fetch('/api/v1/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: userInput,
          template_id: selectedTemplateId || undefined,
        }),
      });

      clearInterval(stepTimer);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to generate report');

      setCurrentStep(5); // Completed
      setPipelineReport(data);
      if (data.versions && data.versions.length > 0) {
        setSelectedVersion(data.versions.length);
      }
    } catch (err: any) {
      clearInterval(stepTimer);
      alert(`Report Generation Error: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Run Vector Similarity Search
  const handleSimilaritySearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await fetch('/api/v1/documents/similarity-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, top_k: 5 }),
      });
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (err) {
      console.error('Similarity search error', err);
    } finally {
      setIsSearching(false);
    }
  };

  // View chunks for a document
  const handleViewDocChunks = async (doc: RefDoc) => {
    setViewingDocTitle(doc.title);
    try {
      const res = await fetch(`/api/v1/documents/${doc.id}/chunks`);
      const chunks = await res.json();
      setSelectedDocChunks(chunks);
    } catch (err) {
      console.error('Failed to load chunks', err);
    }
  };

  // Ingest custom document
  const handleIngestDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDocTitle || !newDocContent) return;
    setIsIngesting(true);
    try {
      const res = await fetch('/api/v1/documents/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newDocTitle,
          document_type: newDocType,
          department: newDocDept,
          content: newDocContent,
        }),
      });
      if (res.ok) {
        setShowUploadModal(false);
        setNewDocTitle('');
        setNewDocContent('');
        await fetchDocuments();
      } else {
        const err = await res.json();
        alert(`Ingestion failed: ${err.error}`);
      }
    } catch (err) {
      alert('Ingestion network error');
    } finally {
      setIsIngesting(false);
    }
  };

  const displayedReport = pipelineReport?.versions?.find((v: any) => v.version_number === selectedVersion)?.content || pipelineReport?.final_content;
  const displayedValidation = pipelineReport?.versions?.find((v: any) => v.version_number === selectedVersion)?.validation_result || pipelineReport?.final_content?._validation_summary;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">IntelliReport AI</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                pgvector RAG + Gemini 3.8
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Multi-Agent Report Generation & Validation System</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex items-center gap-1 bg-slate-800/60 p-1 rounded-xl border border-slate-700/50">
          <button
            onClick={() => setActiveTab('studio')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'studio'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/40'
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            Report Studio
          </button>
          <button
            onClick={() => setActiveTab('rag')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'rag'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/40'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            RAG Knowledge Base
          </button>
          <button
            onClick={() => setActiveTab('schema')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'schema'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/40'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            pgvector & Schema
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'logs'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/40'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Agent Audit Logs
          </button>
          <button
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'code'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/40'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            Backend Architecture
          </button>
        </nav>

        {/* Status Indicators */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            5 Agents Online
          </div>
        </div>
      </header>

      {/* Main Tab Views */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {/* ================================================================ */}
        {/* TAB 1: REPORT STUDIO */}
        {/* ================================================================ */}
        {activeTab === 'studio' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Control Panel: Prompt & Options (5 cols) */}
            <div className="lg:col-span-5 space-y-5">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-400" />
                    User Input Specification
                  </h2>
                  <span className="text-[11px] text-slate-400">Agent 1 Target</span>
                </div>

                {/* Sample Prompts */}
                <div>
                  <label className="text-xs font-medium text-slate-400 mb-1.5 block">Quick Sample Prompts:</label>
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      onClick={() =>
                        setUserInput(
                          'Create an industrial visit report for ABC Technologies.\nThe visit happened on 25 September 2026.\n52 IT students attended.\nTopics included AI, Cloud Computing and DevOps.'
                        )
                      }
                      className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700 transition"
                    >
                      ABC Technologies (52 Students)
                    </button>
                    <button
                      onClick={() =>
                        setUserInput(
                          'Generate a technical visit report for Microsoft Azure Development Center.\nDate: November 12, 2026.\nAttendees: 64 Computer Science undergraduates.\nCore Topics: Microservice Orchestration, Kubernetes, and Zero Trust Cloud Security.'
                        )
                      }
                      className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700 transition"
                    >
                      Azure Cloud Center (64 Students)
                    </button>
                    <button
                      onClick={() =>
                        setUserInput(
                          'Industrial visit report for Tesla Autonomous Robotics Division.\nEvent Date: 18 October 2026.\nParticipants: 35 Robotics and Mechanical Engineering students.\nKey sessions: Computer Vision, Embedded Sensor Fusion, and High-Throughput Manufacturing Automation.'
                        )
                      }
                      className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700 transition"
                    >
                      Tesla Robotics (35 Students)
                    </button>
                  </div>
                </div>

                {/* Input Text Area */}
                <div>
                  <label className="text-xs font-medium text-slate-400 mb-1.5 block">Raw Request / Narrative:</label>
                  <textarea
                    value={userInput}
                    onChange={e => setUserInput(e.target.value)}
                    rows={6}
                    placeholder="Enter the factual details of the event or report..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-sans"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Rule: The system preserves ground-truth user facts. Missing parameters will be detected by Agent 1.
                  </p>
                </div>

                {/* Template Selector */}
                <div>
                  <label className="text-xs font-medium text-slate-400 mb-1.5 block">Report Template:</label>
                  <select
                    value={selectedTemplateId}
                    onChange={e => setSelectedTemplateId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Auto-Detect from Context (Default)</option>
                    {templates.map(t => (
                      <option key={t.id} value={t.id}>
                        {t.name} ({t.report_type})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Launch Button */}
                <button
                  onClick={handleGenerateReport}
                  disabled={isGenerating || !userInput.trim()}
                  className={`w-full py-3 px-4 rounded-xl font-medium text-sm flex items-center justify-center gap-2 shadow-lg transition-all ${
                    isGenerating
                      ? 'bg-blue-600/50 text-blue-200 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/25'
                  }`}
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Executing Multi-Agent Workflow...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Report Pipeline
                    </>
                  )}
                </button>
              </div>

              {/* Agent Workflow Stepper */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    5-Stage Multi-Agent Orchestration
                  </h3>
                  <span className="text-[11px] text-slate-500">Max 2 Retries</span>
                </div>

                <div className="space-y-2.5">
                  {[
                    { num: 1, name: 'Agent 1: Input Analysis', desc: 'Factual extraction into Pydantic schema; check missing fields' },
                    { num: 2, name: 'Agent 2: Semantic Retrieval', desc: 'Vector cosine similarity search in pgvector (top 5 chunks)' },
                    { num: 3, name: 'Agent 3: Report Planner', desc: 'Formal section blueprint adhering to report template' },
                    { num: 4, name: 'Agent 4: Report Generator', desc: 'Synthesizes deep content combining user facts & reference tone' },
                    { num: 5, name: 'Agent 5: Validation & QA', desc: 'Factual audit & checklist; triggers regeneration if score < 0.85' },
                  ].map(step => {
                    const isActive = isGenerating && currentStep === step.num;
                    const isDone = currentStep > step.num || (!isGenerating && pipelineReport);

                    return (
                      <div
                        key={step.num}
                        className={`flex items-start gap-3 p-2.5 rounded-xl border transition-all ${
                          isActive
                            ? 'bg-blue-950/40 border-blue-500/50'
                            : isDone
                            ? 'bg-slate-800/40 border-slate-800'
                            : 'bg-slate-950/30 border-slate-900 text-slate-500'
                        }`}
                      >
                        <div
                          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 shrink-0 ${
                            isActive
                              ? 'bg-blue-500 text-white animate-pulse'
                              : isDone
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : step.num}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className={`text-xs font-medium ${isActive ? 'text-blue-300' : isDone ? 'text-slate-200' : 'text-slate-400'}`}>
                              {step.name}
                            </span>
                            {isActive && <span className="text-[10px] text-blue-400 animate-pulse font-mono">Running...</span>}
                            {isDone && <span className="text-[10px] text-emerald-400 font-mono">Completed</span>}
                          </div>
                          <p className="text-[11px] text-slate-400 mt-0.5">{step.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Right Display Panel: Generated Report & Audit (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              {pipelineReport ? (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
                  {/* Header & Controls */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h1 className="text-xl font-bold text-white tracking-tight">{displayedReport?.title || 'Report Generated'}</h1>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{displayedReport?.subtitle || 'Executive Intelligence Document'}</p>
                    </div>

                    {/* Versions & Export Toolbar */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {pipelineReport.versions && pipelineReport.versions.length > 1 && (
                        <div className="flex items-center gap-1 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800">
                          <span className="text-[11px] text-slate-400">Version:</span>
                          {pipelineReport.versions.map((v: any) => (
                            <button
                              key={v.version_number}
                              onClick={() => setSelectedVersion(v.version_number)}
                              className={`text-[11px] px-2 py-0.5 rounded font-mono font-medium ${
                                selectedVersion === v.version_number
                                  ? 'bg-blue-600 text-white'
                                  : 'text-slate-400 hover:text-white'
                              }`}
                            >
                              v{v.version_number}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Export Dropdown / Buttons */}
                      <a
                        href={`/api/v1/reports/${pipelineReport.id}/export/pdf`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
                      >
                        <Download className="w-3.5 h-3.5 text-blue-400" />
                        PDF
                      </a>
                      <a
                        href={`/api/v1/reports/${pipelineReport.id}/export/docx`}
                        download
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
                      >
                        <Download className="w-3.5 h-3.5 text-emerald-400" />
                        Word (.doc)
                      </a>
                      <a
                        href={`/api/v1/reports/${pipelineReport.id}/export/json`}
                        download
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
                      >
                        <Download className="w-3.5 h-3.5 text-purple-400" />
                        JSON
                      </a>
                    </div>
                  </div>

                  {/* Validation Summary Card */}
                  {displayedValidation && (
                    <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className={`w-4 h-4 ${displayedValidation.is_valid ? 'text-emerald-400' : 'text-amber-400'}`} />
                          <span className="text-xs font-semibold text-slate-200">
                            Agent 5 Quality & Factual Integrity Audit
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-400">Score:</span>
                          <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                            displayedValidation.score >= 0.85 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}>
                            {Math.round(displayedValidation.score * 100)}%
                          </span>
                        </div>
                      </div>

                      {/* Criteria Checklist */}
                      {displayedValidation.checks && (
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
                          {Object.entries(displayedValidation.checks).map(([key, val]) => (
                            <div key={key} className="bg-slate-900 p-2 rounded-lg border border-slate-800 flex items-center justify-between">
                              <span className="text-slate-400 truncate capitalize">{key.replace(/_/g, ' ')}</span>
                              {val ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              ) : (
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Warnings or Issues if any */}
                      {displayedValidation.warnings && displayedValidation.warnings.length > 0 && (
                        <div className="text-[11px] text-amber-300/80 bg-amber-500/5 p-2 rounded-lg border border-amber-500/15">
                          <strong>Advisory Notes:</strong> {displayedValidation.warnings.join(' • ')}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Extracted Metadata Grid */}
                  {displayedReport?.metadata && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs">
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">Target Entity</span>
                        <span className="font-medium text-slate-200">{displayedReport.metadata.organization || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">Event Date</span>
                        <span className="font-medium text-slate-200">{displayedReport.metadata.date || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">Department</span>
                        <span className="font-medium text-slate-200">{displayedReport.metadata.department || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">Attendees</span>
                        <span className="font-medium text-slate-200">{displayedReport.metadata.total_participants || 'N/A'}</span>
                      </div>
                    </div>
                  )}

                  {/* Executive Summary */}
                  {displayedReport?.executive_summary && (
                    <div className="bg-blue-950/20 border-l-4 border-blue-500 p-4 rounded-r-xl space-y-1">
                      <h4 className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Executive Summary</h4>
                      <p className="text-xs leading-relaxed text-slate-300">{displayedReport.executive_summary}</p>
                    </div>
                  )}

                  {/* Sections List */}
                  <div className="space-y-5">
                    {displayedReport?.sections?.map((section: any, idx: number) => (
                      <div key={idx} className="space-y-2 border-b border-slate-800/60 pb-5 last:border-b-0">
                        <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                          <span className="w-5 h-5 rounded bg-slate-800 text-blue-400 flex items-center justify-center text-xs font-mono">
                            {idx + 1}
                          </span>
                          {section.title}
                        </h3>

                        <div className="text-xs leading-relaxed text-slate-300 whitespace-pre-line space-y-2 pl-7">
                          {section.content}
                        </div>

                        {section.bullet_points && section.bullet_points.length > 0 && (
                          <div className="pl-7 pt-1">
                            <ul className="list-disc list-inside space-y-1 text-xs text-slate-400">
                              {section.bullet_points.map((pt: string, pIdx: number) => (
                                <li key={pIdx}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Conclusion */}
                  {displayedReport?.conclusions_and_recommendations && (
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5">
                      <h4 className="text-xs font-semibold text-slate-200">Conclusions & Strategic Recommendations</h4>
                      <p className="text-xs leading-relaxed text-slate-300">{displayedReport.conclusions_and_recommendations}</p>
                    </div>
                  )}
                </div>
              ) : (
                /* Empty Studio State */
                <div className="h-[600px] bg-slate-900/60 border border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center p-8 text-center space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                    <Bot className="w-8 h-8" />
                  </div>
                  <div className="max-w-md space-y-1">
                    <h3 className="text-base font-semibold text-white">Report Generation Engine Ready</h3>
                    <p className="text-xs text-slate-400">
                      Configure your prompt on the left and trigger the 5-Agent pipeline. The AI will extract facts, query pgvector for reference guidance, build a structural plan, author the draft, and validate integrity.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-left max-w-sm w-full text-[11px] text-slate-400">
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                      <strong className="text-slate-200 block mb-0.5">Reference Reports:</strong>
                      Ingested into PostgreSQL + pgvector
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                      <strong className="text-slate-200 block mb-0.5">Integrity Auditing:</strong>
                      Automatic re-drafting on validation failure
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* TAB 2: RAG KNOWLEDGE BASE & SEMANTIC RETRIEVAL */}
        {/* ================================================================ */}
        {activeTab === 'rag' && (
          <div className="space-y-6">
            {/* Top Bar & Ingest Button */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-5 rounded-2xl">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-blue-400" />
                  Reference Document Knowledge Base (RAG)
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Reference reports provide structural patterns, domain vocabulary, and formatting standards.
                </p>
              </div>
              <button
                onClick={() => setShowUploadModal(true)}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-xs font-medium shadow-md transition"
              >
                <UploadCloud className="w-4 h-4" />
                Ingest Reference Document
              </button>
            </div>

            {/* Test Semantic Similarity Search Tool */}
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Search className="w-4 h-4 text-indigo-400" />
                  Live pgvector Similarity Search Simulator
                </h3>
                <span className="text-[11px] text-slate-500 font-mono">text-embedding-004 (768-dim)</span>
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Enter semantic query e.g. 'Kubernetes microservices architecture'..."
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleSimilaritySearch}
                  disabled={isSearching || !searchQuery.trim()}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs font-medium flex items-center gap-2 transition disabled:opacity-50"
                >
                  {isSearching ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  Vector Query
                </button>
              </div>

              {/* Search Results Display */}
              {searchResults.length > 0 && (
                <div className="space-y-2.5 pt-2">
                  <h4 className="text-[11px] font-semibold text-slate-400">Top-K Retrieved Context Chunks (Cosine Distance):</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {searchResults.map((result: any, i: number) => (
                      <div key={i} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-blue-400 truncate max-w-[250px]">
                            {result.document_title}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Sim: {result.similarity_score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed line-clamp-4">{result.content}</p>
                        <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-900">
                          <span>Chunk #{result.chunk_index}</span>
                          <span>Dimension: 768</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Ingested Documents List */}
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Ingested Reference Reports in Database ({documents.length})
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {documents.map(doc => (
                  <div key={doc.id} className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col justify-between space-y-3">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-200">{doc.title}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {doc.document_type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 font-mono">{doc.file_name}</p>
                      <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-2">
                        <span>Dept: {doc.metadata?.department || 'General'}</span>
                        <span>•</span>
                        <span>Year: {doc.metadata?.year || '2025'}</span>
                        <span>•</span>
                        <span className="text-blue-400">{doc.chunk_count || 5} Chunks</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleViewDocChunks(doc)}
                      className="w-full py-1.5 rounded-lg bg-slate-900 hover:bg-slate-850 text-slate-300 text-xs font-medium border border-slate-800 flex items-center justify-center gap-1.5 transition"
                    >
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      Inspect pgvector Chunks
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Chunk Inspector Modal/Drawer */}
            {selectedDocChunks.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-blue-400" />
                    Chunk Inspector for: {viewingDocTitle}
                  </h3>
                  <button
                    onClick={() => setSelectedDocChunks([])}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Close
                  </button>
                </div>

                <div className="space-y-3">
                  {selectedDocChunks.map(chunk => (
                    <div key={chunk.id} className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="font-mono text-blue-400 font-semibold">Chunk Index #{chunk.chunk_index}</span>
                        <span className="font-mono text-[10px] bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                          Embedding: Vector(768)
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-line">{chunk.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================================================================ */}
        {/* TAB 3: DATABASE DESIGN & PGVECTOR SCHEMAS */}
        {/* ================================================================ */}
        {activeTab === 'schema' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-2">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-emerald-400" />
                PostgreSQL + pgvector Relational Architecture
              </h2>
              <p className="text-xs text-slate-400">
                Complete database implementation with 7 normalized tables, foreign keys, timestamps, and HNSW cosine distance vector indexing.
              </p>
            </div>

            {/* Table Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[
                {
                  name: 'users',
                  desc: 'Authentication and report author accounts',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'name', type: 'VARCHAR(255)' },
                    { name: 'email', type: 'VARCHAR(255) UNIQUE' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                  ],
                },
                {
                  name: 'report_templates',
                  desc: 'Configurable report structure blueprints',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'name', type: 'VARCHAR(255)' },
                    { name: 'description', type: 'TEXT' },
                    { name: 'report_type', type: 'VARCHAR(100)' },
                    { name: 'template_structure', type: 'JSONB' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                    { name: 'updated_at', type: 'TIMESTAMPTZ' },
                  ],
                },
                {
                  name: 'reference_documents',
                  desc: 'Ingested PDF/DOCX reference reports',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'title', type: 'VARCHAR(255)' },
                    { name: 'file_name', type: 'VARCHAR(255)' },
                    { name: 'file_path', type: 'VARCHAR(500)' },
                    { name: 'document_type', type: 'VARCHAR(100)' },
                    { name: 'metadata', type: 'JSONB' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                  ],
                },
                {
                  name: 'document_chunks',
                  desc: 'Vectorized segments for similarity search',
                  specialBadge: 'pgvector HNSW (768)',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'document_id', type: 'UUID (FK -> reference_documents)' },
                    { name: 'chunk_index', type: 'INTEGER' },
                    { name: 'content', type: 'TEXT' },
                    { name: 'embedding', type: 'Vector(768)' },
                    { name: 'metadata', type: 'JSONB' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                  ],
                },
                {
                  name: 'generated_reports',
                  desc: 'Master entity representing generation task',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'user_id', type: 'UUID (FK -> users)' },
                    { name: 'report_type', type: 'VARCHAR(100)' },
                    { name: 'input_data', type: 'JSONB' },
                    { name: 'final_content', type: 'JSONB' },
                    { name: 'status', type: 'VARCHAR(50)' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                    { name: 'updated_at', type: 'TIMESTAMPTZ' },
                  ],
                },
                {
                  name: 'report_versions',
                  desc: 'Version history across regeneration retries',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'report_id', type: 'UUID (FK -> generated_reports)' },
                    { name: 'version_number', type: 'INTEGER' },
                    { name: 'content', type: 'JSONB' },
                    { name: 'validation_result', type: 'JSONB' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                  ],
                },
                {
                  name: 'generation_logs',
                  desc: 'Audit trail tracking individual agent steps',
                  cols: [
                    { name: 'id', type: 'UUID (PK)' },
                    { name: 'report_id', type: 'UUID (FK -> generated_reports)' },
                    { name: 'agent_name', type: 'VARCHAR(100)' },
                    { name: 'input_data', type: 'JSONB' },
                    { name: 'output_data', type: 'JSONB' },
                    { name: 'execution_time', type: 'FLOAT (seconds)' },
                    { name: 'status', type: 'VARCHAR(50)' },
                    { name: 'error_message', type: 'TEXT' },
                    { name: 'created_at', type: 'TIMESTAMPTZ' },
                  ],
                },
              ].map((tbl, i) => (
                <div key={i} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-sm font-bold text-blue-400">{tbl.name}</span>
                      {tbl.specialBadge && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {tbl.specialBadge}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 mb-3">{tbl.desc}</p>

                    <div className="space-y-1.5 border-t border-slate-800 pt-2.5">
                      {tbl.cols.map((c, cIdx) => (
                        <div key={cIdx} className="flex items-center justify-between text-[11px]">
                          <span className="font-mono text-slate-300">{c.name}</span>
                          <span className="font-mono text-[10px] text-slate-500">{c.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Alembic & HNSW Indexing Strategy */}
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Vector Indexing & Optimization Strategy
              </h3>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-2">
                <div className="text-emerald-400">-- HNSW Index for sub-millisecond Cosine Vector Search</div>
                <div>CREATE EXTENSION IF NOT EXISTS vector;</div>
                <div>
                  CREATE INDEX idx_document_chunks_embedding_hnsw ON document_chunks
                </div>
                <div className="pl-4 text-blue-400">
                  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* TAB 4: AGENT AUDIT LOGS */}
        {/* ================================================================ */}
        {activeTab === 'logs' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-2">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-400" />
                Pipeline Generation Audit Logs
              </h2>
              <p className="text-xs text-slate-400">
                Live inspection of the <code className="text-blue-400">generation_logs</code> table. Every agent execution, duration, input, and output is persistently recorded.
              </p>
            </div>

            {/* Logs Table */}
            {pipelineReport?.logs && pipelineReport.logs.length > 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 uppercase font-semibold text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4">Agent Name</th>
                        <th className="py-3 px-4">Execution Time</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Timestamp</th>
                        <th className="py-3 px-4">Payload</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {pipelineReport.logs.map((log: GenerationLog) => (
                        <tr key={log.id} className="hover:bg-slate-850/50 transition">
                          <td className="py-3 px-4 font-mono font-medium text-blue-400">{log.agent_name}</td>
                          <td className="py-3 px-4 font-mono text-slate-300">{log.execution_time}s</td>
                          <td className="py-3 px-4">
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                                log.status === 'success'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              }`}
                            >
                              {log.status.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">
                            {new Date(log.created_at).toLocaleTimeString()}
                          </td>
                          <td className="py-3 px-4">
                            <button
                              onClick={() => setActiveLogAgent(activeLogAgent === log.id ? null : log.id)}
                              className="text-xs text-blue-400 hover:underline flex items-center gap-1"
                            >
                              <Eye className="w-3 h-3" />
                              Inspect I/O
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Inspect Modal/Card */}
                {activeLogAgent && (
                  <div className="p-4 bg-slate-950 border-t border-slate-800 space-y-3">
                    {(() => {
                      const log = pipelineReport.logs.find((l: any) => l.id === activeLogAgent);
                      if (!log) return null;
                      return (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                              Agent Input Data:
                            </span>
                            <pre className="bg-slate-900 p-3 rounded-xl border border-slate-800 text-[11px] text-slate-300 overflow-x-auto max-h-60 font-mono">
                              {JSON.stringify(log.input_data, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                              Agent Output Data:
                            </span>
                            <pre className="bg-slate-900 p-3 rounded-xl border border-slate-800 text-[11px] text-slate-300 overflow-x-auto max-h-60 font-mono">
                              {JSON.stringify(log.output_data, null, 2)}
                            </pre>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            ) : (
              <div className="h-64 bg-slate-900 border border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center p-6 text-center space-y-2">
                <Clock className="w-8 h-8 text-slate-600" />
                <p className="text-xs text-slate-400">
                  No generation logs yet. Run a report in Report Studio to inspect real-time agent telemetry!
                </p>
              </div>
            )}
          </div>
        )}

        {/* ================================================================ */}
        {/* TAB 5: BACKEND ARCHITECTURE & SOURCE CODE EXPLORER */}
        {/* ================================================================ */}
        {activeTab === 'code' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* File Tree (4 cols) */}
            <div className="lg:col-span-4 space-y-4">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                    <Code className="w-4 h-4 text-blue-400" />
                    Python Backend Architecture
                  </h3>
                </div>

                <div className="space-y-4 text-xs">
                  {codeTree.map((cat, cIdx) => (
                    <div key={cIdx} className="space-y-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                        {cat.category}
                      </span>
                      <div className="space-y-1">
                        {cat.files.map((file: any) => (
                          <button
                            key={file.path}
                            onClick={() => loadFileContent(file.path)}
                            className={`w-full text-left px-3 py-2 rounded-xl transition flex flex-col ${
                              selectedFile === file.path
                                ? 'bg-blue-600 text-white shadow-sm'
                                : 'bg-slate-950/60 hover:bg-slate-800 text-slate-300'
                            }`}
                          >
                            <span className="font-mono text-xs font-medium">{file.name}</span>
                            <span className={`text-[10px] mt-0.5 line-clamp-1 ${selectedFile === file.path ? 'text-blue-100' : 'text-slate-500'}`}>
                              {file.desc}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Code Viewer (8 cols) */}
            <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3 flex flex-col">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-blue-400 font-semibold">{selectedFile}</span>
                </div>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(fileContent);
                    alert('Copied source code to clipboard!');
                  }}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded bg-slate-800 border border-slate-700"
                >
                  <Copy className="w-3.5 h-3.5" />
                  Copy Code
                </button>
              </div>

              {loadingCode ? (
                <div className="h-96 flex items-center justify-center text-slate-500 text-xs">
                  <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                  Loading file...
                </div>
              ) : (
                <div className="flex-1 overflow-auto rounded-xl bg-slate-950 border border-slate-800 p-4">
                  <pre className="font-mono text-xs text-slate-200 leading-relaxed overflow-x-auto whitespace-pre">
                    {fileContent}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Upload Reference Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-blue-400" />
                Ingest Reference Report Document
              </h3>
              <button onClick={() => setShowUploadModal(false)} className="text-slate-400 hover:text-white text-xs">
                ✕
              </button>
            </div>

            <form onSubmit={handleIngestDocument} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-400 block mb-1 font-medium">Document Title:</label>
                <input
                  type="text"
                  required
                  value={newDocTitle}
                  onChange={e => setNewDocTitle(e.target.value)}
                  placeholder="e.g. AWS Cloud Architecture Visit 2026"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Document Type:</label>
                  <select
                    value={newDocType}
                    onChange={e => setNewDocType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none"
                  >
                    <option value="industrial_visit">Industrial Visit</option>
                    <option value="technical_audit">Technical Audit</option>
                    <option value="general_report">General Report</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Department:</label>
                  <input
                    type="text"
                    value={newDocDept}
                    onChange={e => setNewDocDept(e.target.value)}
                    placeholder="e.g. Computer Science"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Document Content / Text:</label>
                <textarea
                  required
                  rows={7}
                  value={newDocContent}
                  onChange={e => setNewDocContent(e.target.value)}
                  placeholder="Paste reference report text here (will be cleaned, chunked into overlapping segments, embedded via Gemini, and inserted into pgvector)..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-200 focus:outline-none font-sans"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isIngesting}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium flex items-center gap-1.5 shadow"
                >
                  {isIngesting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
                  Ingest & Vectorize
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
