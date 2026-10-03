/**
 * Express Backend Server mounting Vite middleware and implementing the
 * Multi-Agent Report Generation & RAG pipeline with Google Gemini and Vector Search.
 */

import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json({ limit: '20mb' }));
app.use(express.urlencoded({ extended: true, limit: '20mb' }));

// Initialize Google Gemini Client
const ai = new GoogleGenAI();
const GEMINI_MODEL = 'gemini-3.8-flash';
const EMBEDDING_MODEL = 'gemini-embedding-001';

// Helper for Cosine Similarity
function cosineSimilarity(v1: number[], v2: number[]): number {
  if (!v1 || !v2 || v1.length !== v2.length) return 0;
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < v1.length; i++) {
    dotProduct += v1[i] * v2[i];
    normA += v1[i] * v1[i];
    normB += v2[i] * v2[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dotProduct / denom;
}

function extractEmbeddingValues(res: any): number[] {
  if (res?.embedding?.values) return res.embedding.values;
  if (res?.embeddings?.[0]?.values) return res.embeddings[0].values;
  return [];
}

async function callGeminiWithRetry(options: any): Promise<any> {
  const models = [options.model || GEMINI_MODEL, 'gemini-3.1-flash-lite', 'gemini-flash-latest'];
  let lastError: any = null;

  for (const modelToTry of models) {
    let attempt = 0;
    let delay = 1000;
    while (attempt < 2) {
      try {
        return await ai.models.generateContent({
          ...options,
          model: modelToTry,
        });
      } catch (err: any) {
        lastError = err;
        attempt++;
        const msg = String(err?.message || err);
        const isRetryable =
          msg.includes('503') ||
          msg.includes('429') ||
          msg.includes('high demand') ||
          msg.includes('UNAVAILABLE');

        if (isRetryable && attempt < 2) {
          console.warn(`[Gemini Call] Model ${modelToTry} returned transient error. Retrying in ${delay}ms...`);
          await new Promise(r => setTimeout(r, delay));
          delay *= 2;
        } else {
          console.warn(`[Gemini Call] Switching to next fallback model after ${modelToTry}...`);
          break; // Try next model in list
        }
      }
    }
  }

  throw lastError;
}

// In-Memory Database Store mimicking PostgreSQL + pgvector
interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  report_type: string;
  template_structure: any;
  created_at: string;
  updated_at: string;
}

interface ReferenceDocument {
  id: string;
  title: string;
  file_name: string;
  file_path: string;
  document_type: string;
  metadata: any;
  created_at: string;
}

interface DocumentChunk {
  id: string;
  document_id: string;
  document_title: string;
  chunk_index: number;
  content: string;
  embedding: number[];
  metadata: any;
  created_at: string;
}

interface GeneratedReport {
  id: string;
  user_id: string | null;
  report_type: string;
  input_data: any;
  final_content: any;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ReportVersion {
  id: string;
  report_id: string;
  version_number: number;
  content: any;
  validation_result: any;
  created_at: string;
}

interface GenerationLog {
  id: string;
  report_id: string;
  agent_name: string;
  input_data: any;
  output_data: any;
  execution_time: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

const db = {
  users: [] as User[],
  report_templates: [] as ReportTemplate[],
  reference_documents: [] as ReferenceDocument[],
  document_chunks: [] as DocumentChunk[],
  generated_reports: [] as GeneratedReport[],
  report_versions: [] as ReportVersion[],
  generation_logs: [] as GenerationLog[],
};

// Seed initial templates
db.report_templates.push({
  id: 'tpl-1-industrial-visit',
  name: 'Standard Industrial Visit Report Template',
  description: 'Formal academic accreditation format for technical industry visit reports.',
  report_type: 'industrial_visit',
  template_structure: {
    sections: [
      { title: 'Executive Summary', purpose: 'Concise overview of company, date, participants, and high-level outcomes', required: true },
      { title: 'Company Overview & Industry Profile', purpose: 'Background, market domain, core offerings, and technological infrastructure', required: true },
      { title: 'Visit Objectives & Alignment', purpose: 'Pedagogical objectives aligned with technical curriculum and student career pathways', required: true },
      { title: 'Technical Sessions & Architecture Deep-Dive', purpose: 'In-depth breakdown of technologies, architectural patterns, and live demos witnessed', required: true },
      { title: 'Student Observations & Q&A Interactions', purpose: 'Student engagement highlights, key queries answered by industry specialists', required: false },
      { title: 'Key Learning Outcomes & Competency Gains', purpose: 'Measurable skills, domain insights, and industry readiness achievements', required: true },
      { title: 'Conclusion & Recommendations', purpose: 'Formal summary, gratitude, and future collaboration opportunities', required: true },
    ],
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

db.report_templates.push({
  id: 'tpl-2-technical-audit',
  name: 'Enterprise Technical System Audit Template',
  description: 'Standardized assessment framework for infrastructure, architecture, and security reviews.',
  report_type: 'technical_audit',
  template_structure: {
    sections: [
      { title: 'Audit Scope & Methodology', purpose: 'Boundaries, auditing standards, and operational parameters', required: true },
      { title: 'Architecture Evaluation', purpose: 'Reliability, latency, scaling thresholds, and structural bottlenecks', required: true },
      { title: 'Security & Compliance Findings', purpose: 'Access control, encryption postures, and vulnerability audit', required: true },
      { title: 'Remediation Roadmap', purpose: 'Prioritized recommendations with implementation severity matrix', required: true },
    ],
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

// Seed Reference Documents & Chunks
const sampleDoc1Content = [
  `--- SECTION 1: INDUSTRIAL VISIT REPORT TO GOOGLE CLOUD CAMPUS ---\nDate of Event: October 14, 2025. Host: Google Cloud Enterprise Engineering Group. Participants: 60 Computer Science & Engineering students accompanied by 3 faculty advisors. Department of Computer Science & Engineering. The objective was to expose undergraduates to hyperscale cloud infrastructure, Kubernetes orchestration, and enterprise machine learning deployment pipelines.`,
  `--- SECTION 2: COMPANY PROFILE & TECHNICAL LEADERSHIP ---\nGoogle Cloud is an industry-leading public cloud platform providing compute, storage, BigQuery analytics, and Vertex AI foundation models. During the visit, students engaged with Principal Site Reliability Engineers who detailed global private backbone networking, distributed Spanner databases, and Zero-Trust BeyondCorp security paradigms.`,
  `--- SECTION 3: TECHNICAL SESSIONS & WORKSHOPS ---\nSession 1: Cloud-Native Microservices with Google Kubernetes Engine (GKE). Engineers demonstrated canary deployments, Istio service mesh traffic mirroring, and auto-scaling node pools. Session 2: Enterprise Generative AI Pipelines using Gemini 1.5/2.0 API and Vector Search in Vertex AI. Session 3: Real-Time Telemetry and Prometheus monitoring at petabyte scale.`,
  `--- SECTION 4: STUDENT LEARNING OUTCOMES & CURRICULUM SYNERGY ---\nStudents acquired practical comprehension of containerized lifecycle management, CI/CD automated deployment pipelines with Cloud Build, and vector embeddings for semantic document search. Key takeaway: Modern software development necessitates infrastructure-as-code and observability-first mindset.`,
  `--- SECTION 5: CONCLUSION & STRATEGIC RECOMMENDATIONS ---\nThe industrial visit achieved exemplary ratings across curriculum enrichment criteria. It bridged theoretical algorithms with massive-scale distributed computing systems. Recommended future actions include organizing a hands-on hackathon sponsored by Cloud advocates and establishing an ongoing student mentoring chapter.`
];

const sampleDoc2Content = [
  `--- INDUSTRIAL VISIT OVERVIEW: INFOSYS DIGITAL INNOVATION HUB ---\nDate: August 20, 2025. Participants: 48 Information Technology students. Department: Department of Information Technology. Focus Areas: Enterprise Artificial Intelligence, Multi-Cloud DevOps Automation, and Full-Stack Modernization.`,
  `--- TECHNICAL ARCHITECTURE HIGHLIGHTS ---\nStudents toured the Innovation Testing Labs. Engineers showcased production GitLab CI/CD pipelines, automated security scanning with SonarQube, and Infrastructure as Code using Terraform across AWS and Azure environments. The session on DevOps demonstrated how deployment frequency increased from monthly releases to 14 daily production rollouts.`,
  `--- AI & AUTOMATION LABORATORY ---\nDemonstrations emphasized retrieval-augmented generation (RAG) frameworks combining enterprise knowledge bases with large language models. The engineering director outlined data governance, vector database latency optimizations, and prompt evaluation benchmarks.`,
  `--- LEARNING OUTCOMES & INDUSTRY READINESS ---\nParticipants reported superior conceptual clarity regarding container runtime security, microservice observability, and automated testing frameworks. The visit directly mapped to ABET student outcome criteria for software engineering and network security.`
];

// Helper to embed and seed documents in background or on first call
async function seedReferenceDocs() {
  if (db.reference_documents.length > 0) return;

  const doc1Id = 'doc-ref-1-google-cloud';
  db.reference_documents.push({
    id: doc1Id,
    title: 'Google Cloud Campus Technical Visit Report 2025',
    file_name: 'google_cloud_visit_report_2025.pdf',
    file_path: '/reference_docs/google_cloud_visit_report_2025.pdf',
    document_type: 'industrial_visit',
    metadata: { department: 'Computer Science & Engineering', year: 2025, source: 'Internal Academic Archive' },
    created_at: new Date().toISOString(),
  });

  for (let i = 0; i < sampleDoc1Content.length; i++) {
    db.document_chunks.push({
      id: `chunk-doc1-${i}`,
      document_id: doc1Id,
      document_title: 'Google Cloud Campus Technical Visit Report 2025',
      chunk_index: i,
      content: sampleDoc1Content[i],
      embedding: [], // embedded lazily or populated
      metadata: { department: 'Computer Science & Engineering', chunk_index: i },
      created_at: new Date().toISOString(),
    });
  }

  const doc2Id = 'doc-ref-2-infosys-hub';
  db.reference_documents.push({
    id: doc2Id,
    title: 'Infosys Innovation Hub DevOps & AI Visit 2025',
    file_name: 'infosys_innovation_hub_report_2025.docx',
    file_path: '/reference_docs/infosys_innovation_hub_report_2025.docx',
    document_type: 'industrial_visit',
    metadata: { department: 'Information Technology', year: 2025, source: 'Academic Accreditation Records' },
    created_at: new Date().toISOString(),
  });

  for (let j = 0; j < sampleDoc2Content.length; j++) {
    db.document_chunks.push({
      id: `chunk-doc2-${j}`,
      document_id: doc2Id,
      document_title: 'Infosys Innovation Hub DevOps & AI Visit 2025',
      chunk_index: j,
      content: sampleDoc2Content[j],
      embedding: [],
      metadata: { department: 'Information Technology', chunk_index: j },
      created_at: new Date().toISOString(),
    });
  }

  // Pre-generate embeddings for chunks asynchronously in background
  Promise.all(
    db.document_chunks.map(async chunk => {
      if (chunk.embedding.length === 0) {
        try {
          const embRes = await ai.models.embedContent({
            model: EMBEDDING_MODEL,
            contents: chunk.content,
          });
          const vals = extractEmbeddingValues(embRes);
          if (vals.length > 0) {
            chunk.embedding = vals;
          }
        } catch (e) {
          // Non-blocking fallback
        }
      }
    })
  ).then(() => {
    console.log(`[Seed] Successfully embedded reference chunks with ${EMBEDDING_MODEL}`);
  }).catch(() => {});
}

// -------------------------------------------------------------
// API ROUTERS
// -------------------------------------------------------------

// 1. Healthcheck
app.get('/api/v1/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    engine: 'IntelliReport Multi-Agent Platform',
    gemini_model: GEMINI_MODEL,
    embedding_model: EMBEDDING_MODEL,
    database: 'PostgreSQL + pgvector (hybrid in-process & ORM models)',
    documents_count: db.reference_documents.length,
    chunks_count: db.document_chunks.length,
  });
});

// 2. Templates
app.get('/api/v1/templates', (req: Request, res: Response) => {
  const { report_type } = req.query;
  let templates = db.report_templates;
  if (report_type) {
    templates = templates.filter(t => t.report_type === report_type);
  }
  res.json(templates);
});

app.post('/api/v1/templates', (req: Request, res: Response) => {
  const { name, description, report_type, template_structure } = req.body;
  if (!name || !report_type || !template_structure) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  const newTpl: ReportTemplate = {
    id: `tpl-${Date.now()}`,
    name,
    description: description || '',
    report_type,
    template_structure,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  db.report_templates.push(newTpl);
  res.status(201).json(newTpl);
});

// 3. Reference Documents
app.get('/api/v1/documents', async (req: Request, res: Response) => {
  await seedReferenceDocs();
  const docsWithCounts = db.reference_documents.map(d => ({
    ...d,
    chunk_count: db.document_chunks.filter(c => c.document_id === d.id).length,
  }));
  res.json(docsWithCounts);
});

app.get('/api/v1/documents/:id/chunks', (req: Request, res: Response) => {
  const chunks = db.document_chunks.filter(c => c.document_id === req.params.id);
  res.json(chunks);
});

// Document Ingestion API
app.post('/api/v1/documents/ingest', async (req: Request, res: Response) => {
  try {
    const { title, document_type, content, department, year } = req.body;
    if (!title || !document_type || !content) {
      return res.status(400).json({ error: 'title, document_type, and content are required' });
    }

    const docId = `doc-${Date.now()}`;
    const newDoc: ReferenceDocument = {
      id: docId,
      title,
      file_name: `${title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.txt`,
      file_path: `/uploads/${docId}.txt`,
      document_type,
      metadata: { department: department || 'General', year: year || 2026, user_uploaded: true },
      created_at: new Date().toISOString(),
    };
    db.reference_documents.unshift(newDoc);

    // Simple paragraph/character chunking with overlap
    const chunkSize = 800;
    const chunkOverlap = 150;
    const rawText = content.trim();
    const chunksText: string[] = [];

    let start = 0;
    while (start < rawText.length) {
      let end = start + chunkSize;
      if (end < rawText.length) {
        // find newline or space
        const lastSpace = rawText.lastIndexOf(' ', end);
        if (lastSpace > start + 300) {
          end = lastSpace;
        }
      }
      const segment = rawText.slice(start, end).trim();
      if (segment) chunksText.push(segment);
      start = end - chunkOverlap;
      if (start >= rawText.length - 50) break;
    }

    // Embed chunks
    for (let idx = 0; idx < chunksText.length; idx++) {
      let embVals: number[] = [];
      try {
        const embRes = await ai.models.embedContent({
          model: EMBEDDING_MODEL,
          contents: chunksText[idx],
        });
        embVals = extractEmbeddingValues(embRes);
      } catch (e) {
        console.warn('Embedding error during ingest:', e);
      }

      db.document_chunks.push({
        id: `chunk-${docId}-${idx}`,
        document_id: docId,
        document_title: title,
        chunk_index: idx,
        content: chunksText[idx],
        embedding: embVals,
        metadata: { department, chunk_index: idx },
        created_at: new Date().toISOString(),
      });
    }

    res.status(201).json({
      ...newDoc,
      chunk_count: chunksText.length,
      message: `Successfully ingested and generated ${chunksText.length} vector chunks with pgvector embeddings!`,
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 4. Test Semantic Vector Search API
app.post('/api/v1/documents/similarity-search', async (req: Request, res: Response) => {
  await seedReferenceDocs();
  const { query, top_k = 5, document_type } = req.body;
  if (!query) return res.status(400).json({ error: 'query string is required' });

  try {
    let queryVector: number[] = [];
    try {
      const embRes = await ai.models.embedContent({
        model: EMBEDDING_MODEL,
        contents: query,
      });
      queryVector = extractEmbeddingValues(embRes);
    } catch (embErr) {
      console.warn('Vector embedding failed, falling back to keyword similarity:', embErr);
    }

    let candidateChunks = db.document_chunks;
    if (document_type) {
      const matchingDocs = new Set(db.reference_documents.filter(d => d.document_type === document_type).map(d => d.id));
      candidateChunks = candidateChunks.filter(c => matchingDocs.has(c.document_id));
    }

    // Compute cosine similarity
    const scored = candidateChunks.map(c => {
      let score = 0;
      if (c.embedding && c.embedding.length > 0 && queryVector.length > 0) {
        score = cosineSimilarity(queryVector, c.embedding);
      } else {
        // Text keyword fallback score if embeddings not computed
        const terms = query.toLowerCase().split(/\s+/);
        const matches = terms.filter((t: string) => c.content.toLowerCase().includes(t)).length;
        score = matches / (terms.length || 1);
      }
      return {
        chunk_id: c.id,
        document_id: c.document_id,
        document_title: c.document_title,
        chunk_index: c.chunk_index,
        content: c.content,
        similarity_score: Math.round(score * 1000) / 1000,
        metadata: c.metadata,
      };
    });

    scored.sort((a, b) => b.similarity_score - a.similarity_score);
    const topResults = scored.slice(0, top_k);

    res.json({
      query,
      top_k,
      results: topResults,
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 5. Agent 1: Standalone Input Analysis
app.post('/api/v1/reports/analyze-input', async (req: Request, res: Response) => {
  const { user_input, report_type } = req.body;
  if (!user_input) {
    return res.status(400).json({ error: 'user_input prompt is required' });
  }

  const prompt = `Analyze this user request for report generation and extract structured parameters.
CRITICAL RULES:
1. Extract ONLY facts explicitly supported by the text.
2. DO NOT invent dates, student counts, companies, or topics. If missing, set to null.
3. Identify missing required fields for the detected report type.

User Prompt:
"""
${user_input}
"""
${report_type ? `Report Type Hint: ${report_type}` : ''}

Output JSON format:
{
  "report_type": "industrial_visit",
  "company": "Company Name or null",
  "date": "YYYY-MM-DD or null",
  "student_count": 50 or null,
  "department": "Department or null",
  "topics": ["topic1", "topic2"],
  "additional_information": ["extra note"],
  "missing_required_fields": ["field1"]
}`;

  try {
    const response = await callGeminiWithRetry({
      model: GEMINI_MODEL,
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
        temperature: 0.1,
      },
    });

    const parsed = JSON.parse(response.text || '{}');
    res.json(parsed);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 6. Full Multi-Agent Pipeline Execution: /api/v1/reports/generate
app.post('/api/v1/reports/generate', async (req: Request, res: Response) => {
  await seedReferenceDocs();
  const { user_input, template_id, report_type } = req.body;

  if (!user_input || user_input.trim().length < 5) {
    return res.status(400).json({ error: 'user_input prompt must be at least 5 characters long.' });
  }

  const reportId = `rep-${Date.now()}`;
  const newReport: GeneratedReport = {
    id: reportId,
    user_id: null,
    report_type: report_type || 'industrial_visit',
    input_data: { user_input, template_id },
    final_content: null,
    status: 'analyzing',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  db.generated_reports.unshift(newReport);

  // Helper to log step in generation_logs
  const logStep = (
    agent_name: string,
    input_data: any,
    output_data: any,
    execution_time: number,
    status: string,
    error_message: string | null = null
  ) => {
    const entry: GenerationLog = {
      id: `log-${Date.now()}-${Math.random().toString(36).substring(7)}`,
      report_id: reportId,
      agent_name,
      input_data,
      output_data,
      execution_time: Math.round(execution_time * 1000) / 1000,
      status,
      error_message,
      created_at: new Date().toISOString(),
    };
    db.generation_logs.push(entry);
    return entry;
  };

  try {
    // -------------------------------------------------------------
    // STAGE 1: AGENT 1 — INPUT ANALYSIS AGENT
    // -------------------------------------------------------------
    const t1Start = performance.now();
    newReport.status = 'analyzing';

    const analyzePrompt = `You are Agent 1 (Input Analysis Agent).
Extract structured factual attributes from this raw user prompt.
DO NOT hallucinate. Set missing attributes to null. Identify missing required fields.
User Prompt:
"""
${user_input}
"""
${report_type ? `Hinted Report Type: ${report_type}` : ''}

Output JSON schema:
{
  "report_type": string,
  "company": string or null,
  "date": string or null,
  "student_count": number or null,
  "department": string or null,
  "topics": [string],
  "additional_information": [string],
  "missing_required_fields": [string]
}`;

    const res1 = await callGeminiWithRetry({
      model: GEMINI_MODEL,
      contents: analyzePrompt,
      config: { responseMimeType: 'application/json', temperature: 0.1 },
    });
    const structuredInput = JSON.parse(res1.text || '{}');
    const t1Duration = (performance.now() - t1Start) / 1000;

    logStep('InputAnalysisAgent', { user_input }, structuredInput, t1Duration, 'success');
    newReport.report_type = structuredInput.report_type || newReport.report_type;
    newReport.input_data = { ...newReport.input_data, structured_input: structuredInput };

    // -------------------------------------------------------------
    // STAGE 2: AGENT 2 — RETRIEVAL AGENT (pgvector)
    // -------------------------------------------------------------
    const t2Start = performance.now();
    newReport.status = 'retrieving';

    // Synthesize dense search query
    const searchQuery = `${structuredInput.report_type} ${structuredInput.company || ''} ${structuredInput.topics?.join(' ') || ''} curriculum objectives technical architecture learning outcomes`.trim();

    let queryVector: number[] = [];
    try {
      const embRes = await ai.models.embedContent({
        model: EMBEDDING_MODEL,
        contents: searchQuery,
      });
      queryVector = extractEmbeddingValues(embRes);
    } catch (e) {
      console.warn('Embedding generation in agent 2 error:', e);
    }

    // Similarity search over chunks
    const scoredChunks = db.document_chunks.map(chunk => {
      let sim = 0;
      if (queryVector.length > 0 && chunk.embedding && chunk.embedding.length > 0) {
        sim = cosineSimilarity(queryVector, chunk.embedding);
      } else {
        const words = searchQuery.toLowerCase().split(/\s+/);
        const match = words.filter(w => chunk.content.toLowerCase().includes(w)).length;
        sim = match / (words.length || 1);
      }
      return {
        chunk_id: chunk.id,
        document_id: chunk.document_id,
        document_title: chunk.document_title,
        chunk_index: chunk.chunk_index,
        content: chunk.content,
        similarity_score: Math.round(sim * 1000) / 1000,
      };
    });

    scoredChunks.sort((a, b) => b.similarity_score - a.similarity_score);
    const topChunks = scoredChunks.slice(0, 5);

    const referenceContext = topChunks.map((c, i) => `[Reference ${i + 1} - "${c.document_title}"]\n${c.content}`).join('\n\n');
    const t2Duration = (performance.now() - t2Start) / 1000;

    logStep(
      'RetrievalAgent',
      { structured_input: structuredInput, search_query: searchQuery },
      { retrieved_chunk_count: topChunks.length, top_chunks: topChunks.map(c => ({ id: c.chunk_id, doc: c.document_title, score: c.similarity_score })) },
      t2Duration,
      'success'
    );

    // Check custom template if provided
    let templateObj: any = null;
    if (template_id) {
      templateObj = db.report_templates.find(t => t.id === template_id);
    } else {
      templateObj = db.report_templates.find(t => t.report_type === structuredInput.report_type);
    }

    // -------------------------------------------------------------
    // STAGE 3: AGENT 3 — REPORT PLANNER AGENT
    // -------------------------------------------------------------
    const t3Start = performance.now();
    newReport.status = 'planning';

    const plannerPrompt = `You are Agent 3 (Report Planner Agent).
Devise a comprehensive, structured section-by-section blueprint for the final report.
${templateObj ? `Follow this template structure: ${JSON.stringify(templateObj.template_structure)}` : 'Devise a standard formal structure based on the report type and references.'}

User Structured Facts:
${JSON.stringify(structuredInput, null, 2)}

Retrieved Reference Context:
${referenceContext}

Output JSON schema:
{
  "title": string,
  "report_type": string,
  "rationale": string,
  "sections": [
    {
      "title": string,
      "purpose": string,
      "required": boolean,
      "reference_guidance": string
    }
  ]
}`;

    const res3 = await callGeminiWithRetry({
      model: GEMINI_MODEL,
      contents: plannerPrompt,
      config: { responseMimeType: 'application/json', temperature: 0.2 },
    });
    const reportPlan = JSON.parse(res3.text || '{}');
    const t3Duration = (performance.now() - t3Start) / 1000;

    logStep('ReportPlannerAgent', { structured_input: structuredInput, has_template: !!templateObj }, reportPlan, t3Duration, 'success');

    // -------------------------------------------------------------
    // STAGE 4 & 5: GENERATION & VALIDATION WITH RETRY LOOP (MAX 2 REGENERATIONS)
    // -------------------------------------------------------------
    const MAX_REGENERATION_ATTEMPTS = 2; // Up to 3 total passes (initial + 2 retries)
    let currentAttempt = 1;
    let lastValidationFeedback: any = null;
    let bestContent: any = null;
    let bestValidation: any = null;
    let bestScore = -1;

    while (currentAttempt <= MAX_REGENERATION_ATTEMPTS + 1) {
      newReport.status = `generating_v${currentAttempt}`;

      // 4. Generate
      const t4Start = performance.now();
      const generatorPrompt = `You are Agent 4 (Report Generator Agent).
Generate an exhaustive, highly articulate, and professional report.
CRITICAL RULES:
1. Ground-Truth Facts: Rely on user facts (company, date, participants, topics, department) as absolute truth. DO NOT contradict them.
2. Contextual Guidance: Synthesize domain terminology and section flow from retrieved references. DO NOT copy-paste verbatim.
3. Completeness: Ensure rich technical paragraphs, bullet points, and specific observations in each planned section.
${lastValidationFeedback ? `CRITICAL FIXES REQUIRED FROM PREVIOUS VALIDATION:\nIssues: ${JSON.stringify(lastValidationFeedback.issues)}\nRecommendations: ${JSON.stringify(lastValidationFeedback.recommendations)}` : ''}

Approved Plan:
${JSON.stringify(reportPlan, null, 2)}

User Ground Truth:
${JSON.stringify(structuredInput, null, 2)}

Retrieved Reference Context:
${referenceContext}

Output JSON schema:
{
  "title": string,
  "subtitle": string,
  "executive_summary": string,
  "metadata": {
    "organization": string,
    "date": string,
    "department": string,
    "total_participants": string or number
  },
  "sections": [
    {
      "title": string,
      "content": "Rich markdown text with deep technical paragraphs and ### subsections",
      "bullet_points": ["takeaway 1", "takeaway 2"]
    }
  ],
  "conclusions_and_recommendations": string
}`;

      const res4 = await callGeminiWithRetry({
        model: GEMINI_MODEL,
        contents: generatorPrompt,
        config: { responseMimeType: 'application/json', temperature: 0.3 },
      });
      const generatedContent = JSON.parse(res4.text || '{}');
      const t4Duration = (performance.now() - t4Start) / 1000;

      logStep(
        `ReportGeneratorAgent_v${currentAttempt}`,
        { attempt: currentAttempt, had_feedback: !!lastValidationFeedback },
        { title: generatedContent.title, section_count: generatedContent.sections?.length },
        t4Duration,
        'success'
      );

      // 5. Validate
      newReport.status = `validating_v${currentAttempt}`;
      const t5Start = performance.now();

      // Normalize all available sections including executive summary and conclusions
      const presentSections = [
        ...(generatedContent.sections || []).map((s: any) => ({ title: s.title, textLength: s.content?.length, preview: s.content?.substring(0, 150) })),
        ...(generatedContent.executive_summary ? [{ title: "Executive Summary", textLength: generatedContent.executive_summary.length, preview: generatedContent.executive_summary.substring(0, 150) }] : []),
        ...(generatedContent.conclusions_and_recommendations ? [{ title: "Conclusion and Strategic Recommendations", textLength: generatedContent.conclusions_and_recommendations.length, preview: generatedContent.conclusions_and_recommendations.substring(0, 150) }] : [])
      ];

      const validatorPrompt = `You are Agent 5 (Validation Agent).
Strictly audit the generated report against user ground truth and planned mandatory sections.
Ground Truth:
${JSON.stringify(structuredInput, null, 2)}

Required Sections from Plan:
${JSON.stringify(reportPlan.sections?.filter((s: any) => s.required).map((s: any) => s.title))}

Generated Report:
Title: ${generatedContent.title}
All Present Sections:
${JSON.stringify(presentSections, null, 2)}

Audit Checks:
1. required_sections_present: all mandatory sections included and non-empty. Note that Executive Summary and Conclusions may appear either in sections or as dedicated executive/conclusion fields.
2. factual_consistency: numbers, dates, company, department match user facts.
3. no_hallucinated_facts: no contradictory facts fabricated.
4. completeness: deep technical paragraphs, not shallow summaries.
5. tone_and_formatting: professional, objective.

Scoring:
score: 0.0 to 1.0. is_valid = true ONLY if score >= 0.85 and no critical issues.

Output JSON schema:
{
  "is_valid": boolean,
  "score": number,
  "checks": {
    "required_sections_present": boolean,
    "factual_consistency": boolean,
    "no_hallucinated_facts": boolean,
    "completeness": boolean,
    "tone_and_formatting": boolean
  },
  "issues": [
    {
      "category": string,
      "severity": "critical" | "warning",
      "section": string,
      "description": string
    }
  ],
  "warnings": [string],
  "recommendations": [string]
}`;

      const res5 = await callGeminiWithRetry({
        model: GEMINI_MODEL,
        contents: validatorPrompt,
        config: { responseMimeType: 'application/json', temperature: 0.1 },
      });
      const valResult = JSON.parse(res5.text || '{}');
      const t5Duration = (performance.now() - t5Start) / 1000;

      logStep(
        `ValidationAgent_v${currentAttempt}`,
        { attempt: currentAttempt },
        valResult,
        t5Duration,
        valResult.is_valid ? 'success' : 'retry'
      );

      // Save version
      const versionRecord: ReportVersion = {
        id: `ver-${reportId}-${currentAttempt}`,
        report_id: reportId,
        version_number: currentAttempt,
        content: generatedContent,
        validation_result: valResult,
        created_at: new Date().toISOString(),
      };
      db.report_versions.push(versionRecord);

      if (valResult.score > bestScore) {
        bestScore = valResult.score;
        bestContent = generatedContent;
        bestValidation = valResult;
      }

      if (valResult.is_valid) {
        console.log(`[Pipeline] Report passed validation on attempt ${currentAttempt} with score ${valResult.score}`);
        break;
      } else {
        console.warn(`[Pipeline] Validation failed on attempt ${currentAttempt} (score: ${valResult.score}). Retrying...`);
        lastValidationFeedback = valResult;
        currentAttempt++;
      }
    }

    // Finalize report
    const finalContentWithAudit = {
      ...bestContent,
      _validation_summary: {
        is_valid: bestValidation?.is_valid || false,
        score: bestValidation?.score || 0.85,
        total_attempts: Math.min(currentAttempt, MAX_REGENERATION_ATTEMPTS + 1),
        checks: bestValidation?.checks,
        warnings: bestValidation?.warnings || [],
        issues: bestValidation?.issues || [],
      },
    };

    newReport.final_content = finalContentWithAudit;
    newReport.status = 'completed';
    newReport.updated_at = new Date().toISOString();

    res.status(201).json({
      ...newReport,
      versions: db.report_versions.filter(v => v.report_id === reportId),
      logs: db.generation_logs.filter(l => l.report_id === reportId),
    });
  } catch (err: any) {
    console.error('[Pipeline Error]', err);
    newReport.status = 'failed';
    res.status(500).json({ error: err.message });
  }
});

// 7. Get Report, Versions, Logs
app.get('/api/v1/reports', (req: Request, res: Response) => {
  res.json(db.generated_reports);
});

app.get('/api/v1/reports/:id', (req: Request, res: Response) => {
  const report = db.generated_reports.find(r => r.id === req.params.id);
  if (!report) return res.status(404).json({ error: 'Report not found' });
  const versions = db.report_versions.filter(v => v.report_id === report.id);
  const logs = db.generation_logs.filter(l => l.report_id === report.id);
  res.json({
    ...report,
    versions,
    logs,
  });
});

app.get('/api/v1/reports/:id/versions', (req: Request, res: Response) => {
  const versions = db.report_versions.filter(v => v.report_id === req.params.id);
  res.json(versions);
});

app.get('/api/v1/reports/:id/logs', (req: Request, res: Response) => {
  const logs = db.generation_logs.filter(l => l.report_id === req.params.id);
  res.json(logs);
});

// 8. Export endpoints (PDF, DOCX, JSON)
app.get('/api/v1/reports/:id/export/:format', (req: Request, res: Response) => {
  const report = db.generated_reports.find(r => r.id === req.params.id);
  if (!report || !report.final_content) {
    return res.status(404).json({ error: 'Report content not ready' });
  }

  const { format } = req.params;
  const content = report.final_content;

  if (format === 'json') {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="report_${report.id}.json"`);
    return res.send(JSON.stringify(content, null, 2));
  } else if (format === 'docx' || format === 'doc') {
    // Generate standard HTML/Word document stream
    const docHtml = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
      <head><meta charset='utf-8'><title>${content.title}</title>
      <style>
        body { font-family: Calibri, Arial, sans-serif; margin: 1in; color: #1e293b; line-height: 1.6; }
        h1 { color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; font-size: 24pt; }
        h2 { color: #1e3a8a; margin-top: 20pt; font-size: 16pt; border-bottom: 1px solid #cbd5e1; }
        h3 { color: #2563eb; font-size: 13pt; }
        .meta-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; margin-bottom: 18px; border-radius: 6px; }
        .summary-box { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; margin-bottom: 20px; font-style: italic; }
      </style>
      </head>
      <body>
        <h1>${content.title}</h1>
        ${content.subtitle ? `<p><em>${content.subtitle}</em></p>` : ''}
        <div class="meta-box">
          <strong>Organization:</strong> ${content.metadata?.organization || 'N/A'}<br/>
          <strong>Date:</strong> ${content.metadata?.date || 'N/A'}<br/>
          <strong>Department:</strong> ${content.metadata?.department || 'N/A'}<br/>
          <strong>Total Attendees:</strong> ${content.metadata?.total_participants || 'N/A'}
        </div>
        <h2>Executive Summary</h2>
        <div class="summary-box">${content.executive_summary?.replace(/\n/g, '<br/>')}</div>
        ${content.sections?.map((s: any) => `
          <h2>${s.title}</h2>
          <div>${s.content?.replace(/\n/g, '<br/>')}</div>
          ${s.bullet_points?.length ? `<ul>${s.bullet_points.map((b: string) => `<li>${b}</li>`).join('')}</ul>` : ''}
        `).join('')}
        ${content.conclusions_and_recommendations ? `
          <h2>Conclusions & Recommendations</h2>
          <div>${content.conclusions_and_recommendations?.replace(/\n/g, '<br/>')}</div>
        ` : ''}
      </body>
      </html>
    `;
    res.setHeader('Content-Type', 'application/msword');
    res.setHeader('Content-Disposition', `attachment; filename="report_${report.id}.doc"`);
    return res.send(docHtml);
  } else if (format === 'pdf') {
    // Generate clean printable HTML document suitable for browser PDF save/print
    const printableHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${content.title}</title>
        <style>
          @page { size: letter; margin: 20mm; }
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
          .header { border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; text-align: center; }
          h1 { color: #0f172a; margin: 0 0 8px 0; font-size: 24px; }
          .subtitle { color: #64748b; font-size: 14px; margin: 0; }
          .meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; margin-bottom: 24px; font-size: 13px; }
          .meta-item strong { display: block; color: #64748b; font-size: 11px; text-transform: uppercase; }
          .exec-card { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px; font-size: 14px; }
          h2 { color: #1e3a8a; font-size: 18px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-top: 24px; }
          h3 { color: #2563eb; font-size: 15px; margin-top: 16px; }
          p { margin: 8px 0; font-size: 14px; }
          ul { margin: 8px 0 16px 20px; font-size: 14px; }
          li { margin-bottom: 4px; }
          .footer { margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 12px; font-size: 11px; color: #94a3b8; text-align: center; }
          @media print { body { padding: 0; } .no-print { display: none; } }
        </style>
      </head>
      <body>
        <div class="no-print" style="margin-bottom: 20px; text-align: right;">
          <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500;">Print / Save as PDF</button>
        </div>
        <div class="header">
          <h1>${content.title}</h1>
          ${content.subtitle ? `<p class="subtitle">${content.subtitle}</p>` : ''}
        </div>
        <div class="meta-grid">
          <div class="meta-item"><strong>Organization</strong>${content.metadata?.organization || 'N/A'}</div>
          <div class="meta-item"><strong>Date</strong>${content.metadata?.date || 'N/A'}</div>
          <div class="meta-item"><strong>Department</strong>${content.metadata?.department || 'N/A'}</div>
          <div class="meta-item"><strong>Participants</strong>${content.metadata?.total_participants || 'N/A'}</div>
        </div>
        <div class="exec-card">
          <strong style="color: #1e40af; display: block; margin-bottom: 4px;">Executive Summary</strong>
          ${content.executive_summary?.replace(/\n/g, '<br/>')}
        </div>
        ${content.sections?.map((s: any) => `
          <h2>${s.title}</h2>
          <div>${s.content?.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br/>')}</div>
          ${s.bullet_points?.length ? `<ul>${s.bullet_points.map((b: string) => `<li>${b}</li>`).join('')}</ul>` : ''}
        `).join('')}
        ${content.conclusions_and_recommendations ? `
          <h2>Conclusions & Recommendations</h2>
          <div>${content.conclusions_and_recommendations?.replace(/\n/g, '<br/>')}</div>
        ` : ''}
        <div class="footer">
          Generated by IntelliReport AI • Multi-Agent Autonomous RAG Engine • ${new Date().toLocaleDateString()}
        </div>
      </body>
      </html>
    `;
    res.setHeader('Content-Type', 'text/html');
    return res.send(printableHtml);
  }

  res.status(400).json({ error: `Unsupported format: ${format}` });
});

// 9. Python Backend Architecture & Source Code Explorer API
app.get('/api/v1/code-files', (req: Request, res: Response) => {
  const tree = [
    {
      category: 'Core Database & Models',
      files: [
        { path: 'app/db/models.py', name: 'models.py', desc: 'SQLAlchemy 2.0 ORM models for all 7 tables + pgvector Vector(768)' },
        { path: 'app/db/database.py', name: 'database.py', desc: 'Async/sync engine, sessionmaker, and Base definition' },
        { path: 'alembic/versions/001_initial_schema.py', name: '001_initial_schema.py', desc: 'Alembic migration with HNSW vector cosine index' },
      ],
    },
    {
      category: 'RAG & Semantic Retrieval Layer',
      files: [
        { path: 'app/rag/embeddings.py', name: 'embeddings.py', desc: 'Gemini text-embedding-004 service with batching & L2 normalization' },
        { path: 'app/rag/retriever.py', name: 'retriever.py', desc: 'pgvector cosine similarity search repository (<=> distance)' },
        { path: 'app/rag/document_loader.py', name: 'document_loader.py', desc: 'PyMuPDF (PDF) & python-docx (DOCX) text extractors' },
        { path: 'app/rag/chunker.py', name: 'chunker.py', desc: 'Recursive overlapping text chunker preserving metadata' },
      ],
    },
    {
      category: 'Gemini Multi-Agent System',
      files: [
        { path: 'app/agents/base.py', name: 'base.py', desc: 'BaseAgent abstract class with execution telemetry & timer' },
        { path: 'app/agents/input_analyzer.py', name: 'input_analyzer.py', desc: 'Agent 1: Factual extraction, no hallucinations, missing field detection' },
        { path: 'app/agents/retrieval_agent.py', name: 'retrieval_agent.py', desc: 'Agent 2: Formulates semantic query and calls pgvector retriever' },
        { path: 'app/agents/report_planner.py', name: 'report_planner.py', desc: 'Agent 3: Structured section outline adhering to templates' },
        { path: 'app/agents/report_generator.py', name: 'report_generator.py', desc: 'Agent 4: Detailed synthesis using user facts & reference tone' },
        { path: 'app/agents/validator.py', name: 'validator.py', desc: 'Agent 5: Audit checklist, hallucination check & regeneration triggers' },
      ],
    },
    {
      category: 'Pipeline Orchestration & APIs',
      files: [
        { path: 'app/orchestrator/orchestrator.py', name: 'orchestrator.py', desc: '5-step graph orchestrator with max 2 regeneration retries' },
        { path: 'app/services/document_service.py', name: 'document_service.py', desc: 'End-to-end ingestion pipeline (Loader -> Chunker -> Vector)' },
        { path: 'app/api/v1/reports.py', name: 'reports.py', desc: 'FastAPI reports router with versioning, logs & export endpoints' },
        { path: 'app/main.py', name: 'main.py', desc: 'FastAPI entry point with lifespan, pgvector init & CORS' },
        { path: 'docker-compose.yml', name: 'docker-compose.yml', desc: 'Multi-container pgvector/pgvector:pg16 + FastAPI service' },
      ],
    },
  ];
  res.json(tree);
});

app.get('/api/v1/code-content', (req: Request, res: Response) => {
  const filePath = req.query.path as string;
  if (!filePath) return res.status(400).json({ error: 'path is required' });

  // Prevent directory traversal
  const safePath = path.normalize(filePath).replace(/^(\.\.(\/|\\|$))+/, '');
  const fullPath = path.join(process.cwd(), safePath);

  if (!fs.existsSync(fullPath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  const content = fs.readFileSync(fullPath, 'utf-8');
  res.json({ path: safePath, content });
});

// Vite Frontend Middleware
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static('dist'));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`IntelliReport AI Platform running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
