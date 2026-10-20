import { useEffect, useLayoutEffect, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import { moduleById, modules, type ModuleDefinition, type ModuleId } from './modules'
import { href, useRoute, type Route } from './routing'
import {
  uploadFiles,
  createCollection,
  askQuestion,
  createTranslationJob,
  getTranslationJob,
  updateTranslationSegment,
  downloadTranslatedDocument,
  createMeetingJob,
  getMeetingJob,
  getLatestMeetingJob,
  updateMeetingDraft,
  transcribeMeetingAudio,
  listMeetingJobs,
  downloadMeetingDocx,
  type Collection,
  type QuestionResponse,
  type TranslationJob,
  type MeetingJob,
  type MeetingDraft,
} from './api'


const lines = (text: string) => text.split('\n').map((line, index) => <span key={index}>{line}</span>)
const revealedLandingItems = new Set<string>()

function ScrollReveal({ children, className = '', id }: { children: ReactNode; className?: string; id: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(() => revealedLandingItems.has(id))
  const [ready, setReady] = useState(false)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element || visible || matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) { revealedLandingItems.add(id); setVisible(true); return }
    setReady(true)
    const observer = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { revealedLandingItems.add(id); setVisible(true); observer.unobserve(element) } }, { threshold: .16, rootMargin: '0px 0px -8% 0px' })
    observer.observe(element)
    return () => observer.disconnect()
  }, [id, visible])
  return <div ref={ref} data-reveal-ready={ready} className={`reveal ${visible ? 'visible' : ''} ${className}`.trim()}>{children}</div>
}

function Icon({ children }: { children: ReactNode }) { return <span className="icon" aria-hidden="true">{children}</span> }

function BackDock({ route, navigate }: { route: Route; navigate: (route: Route) => void }) {
  if (route.kind === 'landing') return null
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    let lastY = window.scrollY, frame = 0
    const onScroll = () => { if (frame) return; frame = requestAnimationFrame(() => { const y = window.scrollY, delta = y - lastY; if (y <= 8) setVisible(true); else if (Math.abs(delta) > 8) setVisible(delta < 0); lastY = y; frame = 0 }) }
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }); setVisible(true); addEventListener('scroll', onScroll, { passive: true }); return () => { removeEventListener('scroll', onScroll); if (frame) cancelAnimationFrame(frame) }
  }, [route.kind, 'id' in route ? route.id : ''])
  const back = route.kind === 'suite' ? { kind: 'landing' } as Route : route.kind === 'workflow' ? { kind: 'suite' } as Route : { kind: 'workflow', id: route.id } as Route
  const forward = route.kind === 'workflow' ? { kind: 'workspace', id: route.id } as Route : null
  return <nav className={`nav-dock ${visible ? '' : 'is-hidden'}`} aria-label="Page navigation">
    <button aria-label="Home" title="Home" onClick={() => navigate({ kind: 'landing' })}><Icon>⌂</Icon></button>
    <button aria-label="Go back" title="Go back" onClick={() => navigate(back)}><Icon>‹</Icon></button>
    <button aria-label="Go forward" title="Continue" disabled={!forward} onClick={() => forward && navigate(forward)}><Icon>›</Icon></button>
  </nav>
}

function Orb() { return <div className="orb-stage" aria-hidden="true"><i className="orb-ring ring-one" /><i className="orb-ring ring-two" /><i className="orb-ribbon" /><i className="orb" /></div> }

function FlowingPaths() { const paths = ['M-130 40 C120 0 180 540 460 385 C710 245 770 100 1350 220','M-140 75 C120 25 210 570 480 415 C720 270 820 125 1350 248','M-120 110 C150 55 245 600 500 445 C760 300 865 155 1350 276','M-130 150 C170 80 275 630 525 475 C790 335 910 180 1350 304','M-110 190 C190 105 305 660 545 505 C820 365 950 210 1350 332','M-110 230 C220 135 335 690 570 535 C845 400 985 240 1350 360','M-100 270 C245 165 365 710 595 565 C870 435 1025 275 1350 390','M-90 310 C270 195 395 730 620 595 C900 470 1060 305 1350 420','M-80 350 C295 225 425 750 645 625 C925 500 1090 335 1350 450','M-70 390 C320 255 455 765 670 655 C950 530 1120 365 1350 480','M-60 430 C345 285 485 780 695 685 C980 560 1150 395 1350 510','M-50 470 C370 315 515 795 720 715 C1010 590 1180 425 1350 540']; return <div className="paths" aria-hidden="true"><svg viewBox="0 0 1200 720" preserveAspectRatio="none">{paths.map((path) => <path key={path} d={path} />)}</svg></div> }

function Landing({ navigate }: { navigate: (route: Route) => void }) {
  return <main className="landing">
    <section className="hero"><FlowingPaths />
      <div className="content hero-content"><div className="hero-copy"><p className="eyebrow">SYNORA</p><h1>{lines('Intelligence.\nWithout the noise.')}</h1><p className="lede">A modular AI platform for document intelligence, knowledge retrieval, privacy protection, multilingual translation, and meeting intelligence.</p><button className="button primary" onClick={() => navigate({ kind: 'suite' })}>Explore the suite</button></div><Orb /></div><p className="scroll-cue">Scroll to explore</p>
    </section>
    <section className="intro-section"><div className="content glass-section"><ScrollReveal id="suite-copy"><p className="eyebrow">The suite</p><h2>{lines('Five capabilities.\nOne considered experience.')}</h2><p className="lede">Each tool is independently designed around a distinct institutional task. Start with the work at hand.</p></ScrollReveal><div className="module-index">{modules.map((module, index) => <ScrollReveal key={module.id} id={`suite-${module.id}`} className={`capability-reveal delay-${index}`}><a href={`#${module.id}`}><span>{module.name}</span><small>{module.number}</small></a></ScrollReveal>)}</div></div></section>
    {modules.map((module) => <FeatureSection key={module.id} module={module} navigate={navigate} />)}
    <section className="closing"><div className="content glass-section centered"><ScrollReveal id="closing"><p className="eyebrow">SYNORA</p><h2>{lines('Bring clarity to\ninstitutional work.')}</h2><button className="button primary" onClick={() => navigate({ kind: 'suite' })}>Explore the suite</button></ScrollReveal></div></section>
    <footer>© 2026 SYNORA <span>Five independent tools. One private workspace.</span></footer>
  </main>
}

function Lines({ count = 4 }: { count?: number }) { return <div className="micro-lines">{Array.from({ length: count }, (_, index) => <i key={index} />)}</div> }

function FeatureVisual({ id }: { id: ModuleId }) {
  if (id === 'change') return <div className="feature-visual change-visual" aria-hidden="true"><div className="document old"><small>Version A</small><Lines /></div><div className="document new"><small>Version B</small><Lines /></div><div className="compare-chip">⇄ <span>Compare changes</span></div><div className="change-result"><small>Review changes</small><b>Added passage</b><b>Modified clause</b><b>Removed line</b></div></div>
  if (id === 'rag') return <div className="feature-visual rag-visual" aria-hidden="true"><div className="knowledge-stack"><i /><i /><i /></div><div className="question-card">⌕ <span>What guidance applies?</span></div><div className="answer-card"><small>Available source</small><b>Document evidence appears here</b><Lines count={2} /></div></div>
  if (id === 'shield') return <div className="feature-visual shield-visual" aria-hidden="true"><div className="privacy-document"><small>Private document</small><Lines count={6} /><em>Personal detail</em><em>Record number</em></div><div className="shield-chip">Review findings <b>02</b></div></div>
  if (id === 'translate') return <div className="feature-visual translate-visual" aria-hidden="true"><div className="language-card source"><small>Source</small><b>Policy information, made accessible.</b></div><div className="language-arrow">→</div><div className="language-card draft"><small>Draft</small><b>கொள்கை தகவல், அணுகக்கூடியது.</b></div><div className="review-state">English ↔ Tamil</div></div>
  return <div className="feature-visual meeting-visual" aria-hidden="true"><div className="minute-sheet"><small>Meeting record · Draft</small><h3>Academic Council</h3><p><b>Agenda</b><span>Admissions calendar review</span></p><p><b>Decision</b><span>Pending source review</span></p><p><b>Action</b><span>Confirm owner and deadline</span></p></div><div className="minute-note">Illustrative draft structure. Review before finalization.</div></div>
}

function FeatureSection({ module, navigate }: { module: ModuleDefinition; navigate: (route: Route) => void }) {
  const flipped = module.id === 'shield' || module.id === 'meeting'
  return <section id={module.id} className={`feature-section ${flipped ? 'flip' : ''}`}><div className="content feature-layout"><ScrollReveal id={`${module.id}-copy`} className="feature-copy"><p className="eyebrow">{module.number} — {module.name}</p><h2>{lines(module.landingTitle)}</h2><p className="lede">{module.landingDescription}</p><button className="button primary" onClick={() => navigate({ kind: 'workflow', id: module.id })}>Open {module.name}</button></ScrollReveal><ScrollReveal id={`${module.id}-visual`} className="feature-scene"><FeatureVisual id={module.id} /></ScrollReveal></div></section>
}

function Suite({ navigate }: { navigate: (route: Route) => void }) { return <main className="app-page content"><header className="page-header"><p className="eyebrow">Your workspace</p><h1>Choose a focused tool.</h1><p className="lede">Every module operates independently. Nothing moves between tools unless you intentionally download and upload it.</p></header><div className="tool-grid">{modules.map((module) => <button key={module.id} className="tool-card" onClick={() => navigate({ kind: 'workflow', id: module.id })}><small>{module.number} · Independent tool</small><b>{module.name}</b><span>{module.landingDescription}</span><i>↗</i></button>)}</div></main> }

function FlowNodeVisual({ id, index }: { id: ModuleId; index: number }) {
  if (id === 'rag') return index === 0 ? <div className="doc-stack"><i /><i /><i /></div> : index === 1 ? <div className="question-chip">Illustrative question:<br />What does the policy say?</div> : index === 2 ? <div className="context-chip"><i /><i /><i /></div> : <div className="review-cursor" />
  if (id === 'shield') return index === 0 ? <div className="doc-stack"><i /><i /><i /></div> : index === 1 ? <div className="scan-area" /> : index === 2 ? <div className="findings"><i /><i /><i /></div> : <div className="redaction-proof"><i /><i /><i /></div>
  if (id === 'translate') return index === 0 ? <div className="doc-stack"><i /><i /><i /></div> : index === 1 ? <div className="language-chip">English → Tamil<br /><span>Illustrative selection</span></div> : index === 2 ? <div className="draft-pair"><i /><i /></div> : <div className="review-cursor" />
  return index === 0 ? <div className="audio-wave"><i /><i /><i /><i /><i /><i /><i /></div> : index === 1 ? <div className="transcript-stack"><i /><i /><i /></div> : index === 2 ? <div className="topic-cluster"><i /><i /><i /></div> : <div className="minutes-output"><i /><i /><i /></div>
}

type ConnectorPair = readonly [string, string]
type ConnectorGeometry = { width: number; height: number; paths: string[] }
const fallbackGraph = (className: string): ConnectorGeometry => className === 'comparison-connections'
  ? { width: 1000, height: 360, paths: ['M 230 135 C 345 135, 390 175, 500 175', 'M 270 235 C 360 235, 405 190, 500 190', 'M 610 181 C 705 181, 760 160, 825 160'] }
  : { width: 1000, height: 285, paths: ['M 225 143 C 275 80, 320 205, 395 143', 'M 455 143 C 520 205, 570 80, 645 143', 'M 705 143 C 770 80, 820 205, 885 143'] }

const sameGeometry = (a: ConnectorGeometry, b: ConnectorGeometry) => a.width === b.width && a.height === b.height && a.paths.length === b.paths.length && a.paths.every((path, index) => path === b.paths[index])

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => { const query = matchMedia('(prefers-reduced-motion: reduce)'); const update = () => setReduced(query.matches); query.addEventListener('change', update); return () => query.removeEventListener('change', update) }, [])
  return reduced
}

function ConnectorLayer({ containerRef, nodes, pairs, className }: { containerRef: React.RefObject<HTMLDivElement | null>; nodes: React.MutableRefObject<Record<string, HTMLElement | null>>; pairs: readonly ConnectorPair[]; className: string }) {
  const reduced = useReducedMotion()
  const [geometry, setGeometry] = useState<ConnectorGeometry>(() => fallbackGraph(className))
  const pairsRef = useRef(pairs)
  pairsRef.current = pairs
  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return
    let frame = 0
    let settle = 0
    let retries = 0
    const update = () => {
      if (window.innerWidth <= 600) { setGeometry((previous) => sameGeometry(previous, fallbackGraph(className)) ? previous : fallbackGraph(className)); return }
      const bounds = container.getBoundingClientRect()
      if (!bounds.width || !bounds.height) { if (retries++ < 4) frame = requestAnimationFrame(update); return }
      const nextPaths = pairsRef.current.flatMap(([from, to]) => {
        const start = nodes.current[from]?.getBoundingClientRect(), end = nodes.current[to]?.getBoundingClientRect()
        if (!start || !end) return []
        const x1 = start.right - bounds.left, y1 = start.top - bounds.top + start.height / 2
        const x2 = end.left - bounds.left, y2 = end.top - bounds.top + end.height / 2
        const curve = Math.max(28, Math.abs(x2 - x1) * .42)
        return [`M ${x1} ${y1} C ${x1 + curve} ${y1}, ${x2 - curve} ${y2}, ${x2} ${y2}`]
      })
      if (nextPaths.length === pairsRef.current.length) {
        const nextGeometry = { width: Math.round(bounds.width), height: Math.round(bounds.height), paths: nextPaths }
        setGeometry((previous) => sameGeometry(previous, nextGeometry) ? previous : nextGeometry)
      }
      if (!nextPaths.length && retries++ < 4) frame = requestAnimationFrame(update)
    }
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(update) }
    const resize = 'ResizeObserver' in window ? new ResizeObserver(schedule) : null
    resize?.observe(container); Object.values(nodes.current).forEach((node) => node && resize?.observe(node))
    window.addEventListener('resize', schedule); schedule(); settle = window.setTimeout(schedule, 760)
    return () => { cancelAnimationFrame(frame); clearTimeout(settle); resize?.disconnect(); window.removeEventListener('resize', schedule) }
  }, [containerRef, nodes])
  return <svg className={className} width="100%" height="100%" viewBox={`0 0 ${geometry.width} ${geometry.height}`} preserveAspectRatio="none" aria-hidden="true">{geometry.paths.map((path, index) => <g key={path}><path d={path} />{!reduced && <circle r="3" fill="#f5f5f5"><animateMotion dur="3s" begin={`${index}s`} repeatCount="indefinite" path={path} /></circle>}</g>)}</svg>
}

function ChangeWorkflow() {
  const containerRef = useRef<HTMLDivElement>(null), nodes = useRef<Record<string, HTMLDivElement | null>>({})
  const pairs: readonly ConnectorPair[] = [['version-a', 'hub'], ['version-b', 'hub'], ['hub', 'result']]
  return <div className="compare-diagram" ref={containerRef}><ConnectorLayer className="comparison-connections" containerRef={containerRef} nodes={nodes} pairs={pairs} /><div ref={(node) => { nodes.current['version-a'] = node }} className="compare-node version-a"><small>Version A · Original</small><Lines /></div><div ref={(node) => { nodes.current['version-b'] = node }} className="compare-node version-b"><small>Version B · Revised</small><Lines /></div><div ref={(node) => { nodes.current.hub = node }} className="compare-node compare-hub"><b>⇄</b><strong>Compare passages</strong><small>Two versions · one review</small></div><div ref={(node) => { nodes.current.result = node }} className="compare-node compare-result"><small>Review changes · Draft</small><p>● Added passage</p><p>○ Modified clause</p><p>× Removed line</p></div></div>
}

function OrbitWorkflow({ module }: { module: ModuleDefinition }) {
  const containerRef = useRef<HTMLDivElement>(null), nodes = useRef<Record<string, HTMLElement | null>>({})
  const ids = module.steps.map((_, index) => `step-${index}`)
  return <div className={`orbit-scene ${module.id}-orbit`} ref={containerRef}><span className="technical-corner top-left" /><span className="technical-corner top-right" /><span className="technical-corner bottom-left" /><span className="technical-corner bottom-right" /><ConnectorLayer className="orbit-connections" containerRef={containerRef} nodes={nodes} pairs={ids.slice(0, -1).map((id, index) => [id, ids[index + 1]] as ConnectorPair)} />{module.steps.map((step, index) => <article key={step.title} ref={(node) => { nodes.current[ids[index]] = node }} className="orbit-node" style={{ '--n': index } as React.CSSProperties}><span className="node-kicker">0{index + 1}</span><FlowNodeVisual id={module.id} index={index} /><b>{step.title}</b><small>{step.description}</small></article>)}</div>
}

function WorkflowDiagram({ module }: { module: ModuleDefinition }) { const change = module.id === 'change'; return <section className={`workflow-card ${change ? 'change-workflow' : 'orbit-workflow'}`}><header><b>{module.workflowTitle}</b><span>Illustrative flow</span></header>{change ? <ChangeWorkflow /> : <OrbitWorkflow module={module} />}<div className="workflow-caption orbit-captions"><div><h3>{change ? 'From versions to differences' : 'From input to structured context'}</h3><p>The stages describe how this independent workspace organizes information for review.</p></div><div><h3>Review remains in control</h3><p>This illustration is conceptual; results depend on configured services and source material.</p></div></div></section> }

function Workflow({ module, navigate }: { module: ModuleDefinition; navigate: (route: Route) => void }) { return <main className="app-page content"><header className="page-header"><p className="eyebrow">{module.workflowTitle}</p><h1>{lines(module.workflowHeading)}</h1><p className="lede">{module.workflowDescription}</p></header><WorkflowDiagram module={module} /><div className="continue"><button className="button primary" onClick={() => navigate({ kind: 'workspace', id: module.id })}>Continue to {module.name}</button></div></main> }

function FileInput({ label, accept = '.txt,.pdf' }: { label: string; accept?: string }) { const [file, setFile] = useState<string>(); const ref = useRef<HTMLInputElement>(null); const pick = (event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0]?.name); return <div className="upload-box"><input ref={ref} type="file" accept={accept} onChange={pick} /><b>{label}</b><span>{file ?? 'PDF or TXT · up to 20 MB'}</span><button className="button secondary" type="button" onClick={() => ref.current?.click()}>{file ? 'Change file' : 'Choose file'}</button></div> }

type LocalFile = { id: string; file: File }
const formatBytes = (bytes: number) => bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`

function FileQueue({ title, accept, files, onChange, multiple = true, maxMb = 20, hint }: { title: string; accept: string[]; files: LocalFile[]; onChange: (files: LocalFile[]) => void; multiple?: boolean; maxMb?: number; hint: string }) {
  const input = useRef<HTMLInputElement>(null), [error, setError] = useState<string>(), [dragging, setDragging] = useState(false)
  const add = (list: FileList | null) => { if (!list) return; const incoming = Array.from(list), next: LocalFile[] = []; for (const file of incoming) { const extension = `.${file.name.split('.').pop()?.toLowerCase()}`; if (!accept.includes(extension)) { setError(`${file.name} is not a supported file type.`); continue } if (file.size > maxMb * 1024 * 1024) { setError(`${file.name} exceeds the ${maxMb} MB limit.`); continue } if (files.some((item) => item.file.name === file.name && item.file.size === file.size) || next.some((item) => item.file.name === file.name && item.file.size === file.size)) { setError(`${file.name} is already selected.`); continue } next.push({ id: `${file.name}-${file.size}-${file.lastModified}`, file }) } if (next.length) { setError(undefined); onChange(multiple ? [...files, ...next] : [next[0]]) } }
  return <section className={`file-queue ${dragging ? 'is-dragging' : ''}`}><input ref={input} className="visually-hidden" type="file" accept={accept.join(',')} multiple={multiple} onChange={(event) => add(event.target.files)} /><div className="queue-dropzone" role="button" tabIndex={0} onClick={() => input.current?.click()} onKeyDown={(event) => event.key === 'Enter' && input.current?.click()} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); add(event.dataTransfer.files) }}><b>{title}</b><span>{hint}</span><span className="queue-action">Choose files or drag them here</span></div>{error && <p className="upload-error" role="alert">{error}</p>}{files.length ? <ul className="file-list" aria-label={`${title} selected files`}>{files.map(({ id, file }) => <li key={id}><span><b>{file.name}</b><small>{file.type || file.name.split('.').pop()?.toUpperCase()} · {formatBytes(file.size)} · Selected locally</small></span><button className="icon-button" type="button" aria-label={`Remove ${file.name}`} onClick={() => onChange(files.filter((item) => item.id !== id))}>×</button></li>)}</ul> : <p className="queue-empty">No files selected.</p>}</section>
}

function RagWorkspace() {
  const documentTypes = ['.pdf', '.docx', '.txt']
  const [ragFiles, setRagFiles] = useState<LocalFile[]>([])
  const [collectionName, setCollectionName] = useState('Institutional Policy Collection')
  const [question, setQuestion] = useState('')
  const [collection, setCollection] = useState<Collection | null>(null)
  const [result, setResult] = useState<QuestionResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleAsk = async () => {
    if (!ragFiles.length) {
      setError('Please add at least one document to the collection.')
      return
    }
    if (!question.trim()) {
      setError('Please enter a question to ask the collection.')
      return
    }

    setError(null)
    setIsLoading(true)

    try {
      let currentCollection = collection
      if (!currentCollection) {
        setStatusMessage('Uploading documents to secure local storage...')
        const uploaded = await uploadFiles(ragFiles.map((f) => f.file), 'rag')

        setStatusMessage('Extracting text and indexing vector embeddings...')
        const fileIds = uploaded.map((u) => u.id)
        currentCollection = await createCollection(collectionName || 'Default Collection', fileIds)
        setCollection(currentCollection)
      }

      setStatusMessage('Retrieving evidence and formulating answer...')
      const response = await askQuestion(currentCollection.id, question)
      setResult(response)
      setStatusMessage(null)
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred during RAG processing.')
      setStatusMessage(null)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="workspace-flow">
      <label className="field">
        Collection name
        <input
          value={collectionName}
          onChange={(e) => setCollectionName(e.target.value)}
          placeholder="e.g. Admissions policies"
        />
      </label>
      <FileQueue
        title="Add documents to start a collection"
        accept={documentTypes}
        files={ragFiles}
        onChange={(files) => {
          setRagFiles(files)
          setCollection(null)
          setResult(null)
        }}
        hint="PDF, DOCX, or TXT · up to 20 MB each"
      />
      <p className="integration-state">
        {collection
          ? `Indexed collection '${collection.name}' (${collection.chunkCount} passages, provider: ${collection.embeddingProvider || 'local'}${collection.embeddingDim ? `, ${collection.embeddingDim}-dim` : ''}).`
          : ragFiles.length
          ? `${ragFiles.length} document(s) queued. Clicking 'Ask collection' will upload and index them in the private vector store.`
          : 'Select documents before a collection can be indexed.'}
      </p>
      <label className="field">
        Question
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question grounded in your collection…"
        />
      </label>
      {error && (
        <div className="status-banner error" role="alert">
          {error}
          {error.includes('mismatch') && (
            <div style={{ marginTop: '8px' }}>
              <button
                type="button"
                className="button secondary"
                style={{ fontSize: '12px', padding: '4px 10px' }}
                onClick={() => {
                  setCollection(null)
                  setError(null)
                  handleAsk()
                }}
              >
                Re-index collection with active provider
              </button>
            </div>
          )}
        </div>
      )}
      {statusMessage && (
        <div className="status-indicator">
          <div className="spinner" />
          <span>{statusMessage}</span>
        </div>
      )}
      <button
        className="button primary"
        disabled={!ragFiles.length || !question.trim() || isLoading}
        onClick={handleAsk}
      >
        {isLoading ? 'Processing…' : 'Ask collection'}
      </button>

      <section className="evidence-panel">
        <b>Grounded answer & evidence</b>
        {!result && !isLoading && (
          <p>No answer is available until the selected documents have been securely indexed and retrieved.</p>
        )}
        {result && (
          <div>
            <div className="answer-box">
              {result.answer}
            </div>
            {result.evidenceFound && result.citations.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <b style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--sub)' }}>
                  Inspectable Evidence ({result.citations.length} citation{result.citations.length > 1 ? 's' : ''})
                </b>
                <ul className="citations-list">
                  {result.citations.map((c, i) => (
                    <li key={i} className="citation-card">
                      <div className="citation-header">
                        <span style={{ fontWeight: 600 }}>{c.name}</span>
                        <span className="citation-badge">
                          {c.page ? `Page ${c.page}` : c.section || 'General'}
                        </span>
                      </div>
                      <div className="citation-excerpt">"{c.excerpt}"</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!result.evidenceFound && (
              <div className="status-banner warning" style={{ marginTop: '14px' }}>
                No citations available. The system identified insufficient evidence in the collection and declined to fabricate an answer.
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

function TranslateWorkspace() {
  const documentTypes = ['.pdf', '.docx', '.txt']
  const [translateFiles, setTranslateFiles] = useState<LocalFile[]>([])
  const [sourceLang, setSourceLang] = useState('English')
  const [targetLang, setTargetLang] = useState('Tamil')
  const [sourceText, setSourceText] = useState('')
  const [job, setJob] = useState<TranslationJob | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async () => {
    if (!job) return
    setIsDownloading(true)
    setError(null)
    try {
      const { blob, filename } = await downloadTranslatedDocument(job.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(`Download failed: ${err.message}`)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleTranslate = async () => {
    if (!translateFiles.length && !sourceText.trim()) {
      setError('Please provide a document or paste source text to translate.')
      return
    }

    if (sourceLang.toLowerCase() === targetLang.toLowerCase()) {
      setError('Source and target languages cannot be identical. Please select distinct languages.')
      return
    }

    setError(null)
    setIsLoading(true)
    setStatusMessage('Uploading and extracting source content...')

    try {
      let fileIds: string[] = []
      if (translateFiles.length) {
        const uploaded = await uploadFiles(translateFiles.map((f) => f.file), 'translate')
        fileIds = uploaded.map((u) => u.id)
      }

      setStatusMessage(`Submitting translation task...`)
      const res = await createTranslationJob({
        fileIds,
        sourceText: sourceText.trim() || undefined,
        sourceLanguage: sourceLang,
        targetLanguage: targetLang,
      })

      setStatusMessage(`Fetching translation draft...`)
      // Fetch and poll GET /api/translate/jobs/{job_id}
      let currentJob = await getTranslationJob(res.id)
      let attempts = 0
      while ((currentJob.status === 'queued' || currentJob.status === 'processing') && attempts < 30) {
        await new Promise((resolve) => setTimeout(resolve, 500))
        currentJob = await getTranslationJob(res.id)
        attempts++
      }

      if (currentJob.status === 'failed') {
        setError(currentJob.error || 'Translation job failed.')
        setJob(null)
      } else {
        setJob(currentJob)
      }
      setStatusMessage(null)
    } catch (err: any) {
      setError(err.message || 'An error occurred during translation.')
      setStatusMessage(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSegmentEdit = async (
    segmentId: string,
    newText: string,
    reviewFlag: 'unreviewed' | 'approved' | 'edited' | 'no_model'
  ) => {
    if (!job) return
    try {
      const updated = await updateTranslationSegment(job.id, segmentId, newText, reviewFlag)
      setJob(updated)
    } catch (err: any) {
      setError(`Failed to save edit: ${err.message}`)
    }
  }

  return (
    <div className="workspace-flow">
      <FileQueue
        title="Upload institutional document"
        accept={documentTypes}
        files={translateFiles}
        onChange={(files) => {
          setTranslateFiles(files)
          setJob(null)
        }}
        hint="PDF, DOCX, or TXT · up to 20 MB each"
      />
      <div className="two-up">
        <label className="field">
          Source language
          <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
            <option>English</option>
            <option>Tamil</option>
            <option>Hindi</option>
            <option>Telugu</option>
            <option>Kannada</option>
            <option>Malayalam</option>
          </select>
        </label>
        <label className="field">
          Target language
          <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
            <option>Tamil</option>
            <option>Hindi</option>
            <option>Telugu</option>
            <option>Kannada</option>
            <option>Malayalam</option>
            <option>Bengali</option>
            <option>Marathi</option>
          </select>
        </label>
      </div>
      <label className="field">
        Optional source text
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          placeholder="Paste a short passage only when a document is not available…"
        />
      </label>
      <p className="integration-state">
        {job
          ? `Translation job completed (${job.segments.length} segment${job.segments.length > 1 ? 's' : ''}). All segments are editable drafts.`
          : 'Document extraction and translation are ready. The original file remains unchanged.'}
      </p>
      {error && <div className="status-banner error" role="alert">{error}</div>}
      {statusMessage && (
        <div className="status-indicator">
          <div className="spinner" />
          <span>{statusMessage}</span>
        </div>
      )}
      <button
        className="button primary"
        disabled={(!translateFiles.length && !sourceText.trim()) || isLoading}
        onClick={handleTranslate}
      >
        {isLoading ? 'Translating…' : 'Extract and translate'}
      </button>

      <section className="translation-review">
        <b>Translation review & editing</b>
        {!job && !isLoading && (
          <p>Original and translated content will appear here side by side after real extraction and translation are available.</p>
        )}
        {job && (
          <div>
            <div className="status-banner warning" style={{ margin: '12px 0' }}>
              {job.limitations?.[0] || 'Machine translation draft. Human review required before institutional publication.'}
            </div>
            <div className="segment-list">
              {job.segments.map((seg) => {
                const isNoModel = seg.reviewFlag === 'no_model' || !seg.translated?.trim()
                const tagLabel = isNoModel
                  ? 'No translation model configured'
                  : seg.reviewFlag === 'approved'
                  ? '✓ Approved'
                  : seg.reviewFlag === 'edited'
                  ? '✎ Edited'
                  : 'Review required'

                const blockLabel = seg.blockType === 'heading'
                  ? `Heading ${seg.blockLevel || 1}`
                  : seg.blockType === 'bullet'
                  ? 'Bullet item'
                  : seg.blockType === 'table_cell'
                  ? `Table ${((seg.tableIndex ?? 0) + 1)} · Cell [R${((seg.rowIndex ?? 0) + 1)}, C${((seg.cellIndex ?? 0) + 1)}]`
                  : null

                return (
                  <div key={seg.id} className="segment-card">
                    <div className="segment-source">
                      <small style={{ display: 'block', marginBottom: '4px', color: 'var(--muted)' }}>
                        Source ({job.sourceLanguage})
                        {blockLabel && <span style={{ marginLeft: '6px', opacity: 0.85, fontWeight: 500 }}>· {blockLabel}</span>}
                      </small>
                      {seg.source}
                    </div>
                    <div className="segment-target">
                      <div className="segment-actions">
                        <small style={{ color: 'var(--muted)' }}>Draft ({job.targetLanguage})</small>
                        <button
                          type="button"
                          className={`review-tag ${isNoModel ? 'no-model' : seg.reviewFlag}`}
                          title={isNoModel ? 'Translation model is not configured. Type draft manually.' : 'Click to toggle status'}
                          onClick={() => {
                            if (isNoModel) return
                            const nextFlag = seg.reviewFlag === 'approved' ? 'unreviewed' : 'approved'
                            handleSegmentEdit(seg.id, seg.translated, nextFlag)
                          }}
                        >
                          {tagLabel}
                        </button>
                      </div>
                      <textarea
                        className="segment-textarea"
                        value={seg.translated}
                        placeholder={
                          isNoModel
                            ? 'No translation model is configured. Enter translation draft manually…'
                            : 'Enter or refine translation draft…'
                        }
                        onChange={(e) => {
                          const val = e.target.value
                          setJob({
                            ...job,
                            segments: job.segments.map((s) => s.id === seg.id ? { ...s, translated: val, reviewFlag: 'edited' } : s)
                          })
                        }}
                        onBlur={(e) => handleSegmentEdit(seg.id, e.target.value, 'edited')}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>

      {job && job.status === 'completed' && job.segments.length > 0 && (
        <section className="download-section" style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
          <b>Download translated document</b>
          <p style={{ color: 'var(--sub)', fontSize: '13px', marginBottom: '12px' }}>
            The downloaded file will contain your latest edits. For PDF inputs, download produces a DOCX file (PDF visual layout cannot be reproduced from translated text).
          </p>
          <button
            className="button secondary"
            disabled={isDownloading}
            onClick={handleDownload}
          >
            {isDownloading ? 'Preparing download…' : '⬇ Download translated document'}
          </button>
        </section>
      )}
    </div>
  )
}

function MeetingWorkspace() {
  const [audioFiles, setAudioFiles] = useState<LocalFile[]>([])
  const [transcriptFiles, setTranscriptFiles] = useState<LocalFile[]>([])
  const [meetingTitle, setMeetingTitle] = useState('Institutional Meeting')
  const [transcriptText, setTranscriptText] = useState('')
  const [job, setJob] = useState<MeetingJob | null>(null)
  const [draft, setDraft] = useState<MeetingDraft | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Saved drafts state & tabs
  const [activeTab, setActiveTab] = useState<'editor' | 'saved'>('editor')
  const [savedDrafts, setSavedDrafts] = useState<MeetingJob[]>([])
  const [isLoadingSaved, setIsLoadingSaved] = useState(false)
  const [isDownloading, setIsDownloading] = useState<string | null>(null)

  const refreshSavedDrafts = async () => {
    try {
      setIsLoadingSaved(true)
      const list = await listMeetingJobs()
      setSavedDrafts(list)
    } catch {
      // Graceful fallback
    } finally {
      setIsLoadingSaved(false)
    }
  }

  // Restore latest draft or active job on component mount / browser refresh
  useEffect(() => {
    let isMounted = true
    const restoreActiveJob = async () => {
      refreshSavedDrafts()
      const activeJobId = localStorage.getItem('synora_active_meeting_job_id')
      let loadedJob: MeetingJob | null = null

      if (activeJobId) {
        try {
          loadedJob = await getMeetingJob(activeJobId)
        } catch {
          // If active ID is missing or invalid, fall back to latest
        }
      }

      if (!loadedJob) {
        try {
          loadedJob = await getLatestMeetingJob()
        } catch {
          // No latest job
        }
      }

      if (isMounted && loadedJob) {
        setJob(loadedJob)
        if (loadedJob.draft) {
          setDraft(loadedJob.draft)
          setMeetingTitle(loadedJob.draft.title || 'Institutional Meeting')
        }
        if (loadedJob.transcript) {
          setTranscriptText(loadedJob.transcript)
        }
      }
    }

    restoreActiveJob()
    return () => { isMounted = false }
  }, [])

  const handleTranscribeAudio = async () => {
    if (!audioFiles.length) {
      setError('Please upload an audio recording (.mp3, .wav, or .m4a) to transcribe.')
      return
    }

    setError(null)
    setSaveMessage(null)
    setSaveError(null)
    setIsTranscribing(true)
    setStatusMessage('Uploading audio recording for transcription...')

    try {
      const audioUp = await uploadFiles([audioFiles[0].file], 'meeting')
      if (!audioUp.length) throw new Error('Audio file upload failed.')

      setStatusMessage('Transcribing audio locally with OpenAI Whisper (timestamps preserved)...')
      const res = await transcribeMeetingAudio(audioUp[0].id)
      setTranscriptText(res.transcript)
      setStatusMessage(null)
      setSaveMessage(`Audio recording successfully transcribed (${res.audioFileName}). You can review and edit below, then generate draft minutes.`)
      setTimeout(() => setSaveMessage(null), 6000)
    } catch (err: any) {
      setError(err.message || 'Audio transcription failed.')
      setStatusMessage(null)
    } finally {
      setIsTranscribing(false)
    }
  }

  const handleGenerate = async () => {
    const hasText = Boolean(transcriptText.trim())
    if (!audioFiles.length && !transcriptFiles.length && !hasText) {
      setError('Please upload an audio recording, upload a transcript file, or enter transcript text.')
      return
    }

    setError(null)
    setSaveMessage(null)
    setSaveError(null)
    setIsLoading(true)

    try {
      let audioFileIds: string[] = []
      let transcriptFileIds: string[] = []

      // If user has edited or entered transcript text, use that directly
      if (hasText) {
        setStatusMessage('Reconciling evidence and drafting minutes from edited transcript...')
        const res = await createMeetingJob({
          rawTranscriptText: transcriptText.trim(),
          meetingTitle: meetingTitle || undefined,
        })

        if (res.status === 'failed') {
          setError(res.error || 'ForumNotes generation failed.')
          setJob(null)
          setDraft(null)
        } else {
          setJob(res)
          setDraft(res.draft || null)
          if (res.transcript) setTranscriptText(res.transcript)
          if (res.draft?.title) setMeetingTitle(res.draft.title)
          localStorage.setItem('synora_active_meeting_job_id', res.id)
          refreshSavedDrafts()
        }
      } else {
        setStatusMessage('Uploading meeting source files...')
        if (audioFiles.length) {
          const audioUp = await uploadFiles(audioFiles.map((f) => f.file), 'meeting')
          audioFileIds = audioUp.map((u) => u.id)
        }
        if (transcriptFiles.length) {
          const transUp = await uploadFiles(transcriptFiles.map((f) => f.file), 'meeting')
          transcriptFileIds = transUp.map((u) => u.id)
        }

        setStatusMessage('Extracting proceedings, reconciling evidence, and drafting minutes...')
        const res = await createMeetingJob({
          audioFileIds,
          transcriptFileIds,
          meetingTitle: meetingTitle || undefined,
        })

        if (res.status === 'failed') {
          setError(res.error || 'ForumNotes generation failed.')
          setJob(null)
          setDraft(null)
        } else {
          setJob(res)
          setDraft(res.draft || null)
          if (res.transcript) setTranscriptText(res.transcript)
          if (res.draft?.title) setMeetingTitle(res.draft.title)
          localStorage.setItem('synora_active_meeting_job_id', res.id)
          refreshSavedDrafts()
        }
      }
      setStatusMessage(null)
    } catch (err: any) {
      setError(err.message || 'An error occurred during ForumNotes generation.')
      setStatusMessage(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveDraft = async () => {
    if (!job || !draft) return
    setError(null)
    setSaveError(null)
    setSaveMessage(null)
    setIsSaving(true)

    try {
      // Ensure title in draft is synchronized with the latest input value
      const currentTitle = draft.title?.trim() || meetingTitle.trim() || 'Institutional Meeting'
      const draftToSave: MeetingDraft = {
        ...draft,
        title: currentTitle,
      }

      const updatedJob = await updateMeetingDraft(job.id, draftToSave)
      setJob(updatedJob)
      if (updatedJob.draft) {
        setDraft(updatedJob.draft)
        setMeetingTitle(updatedJob.draft.title)
      }
      localStorage.setItem('synora_active_meeting_job_id', job.id)
      setSaveMessage(`Draft edits successfully saved (Title: "${currentTitle}").`)
      setTimeout(() => setSaveMessage(null), 5000)
      refreshSavedDrafts()
    } catch (err: any) {
      setSaveError(`Failed to save draft edits: ${err.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDownloadCurrentDocx = async () => {
    if (!job || !draft) return
    setError(null)
    setIsDownloading('current')
    try {
      // Save latest draft edits first so DOCX uses latest edits
      const currentTitle = draft.title?.trim() || meetingTitle.trim() || 'Institutional Meeting'
      const draftToSave: MeetingDraft = { ...draft, title: currentTitle }
      const updatedJob = await updateMeetingDraft(job.id, draftToSave)
      setJob(updatedJob)
      if (updatedJob.draft) {
        setDraft(updatedJob.draft)
        setMeetingTitle(updatedJob.draft.title)
      }

      const { blob, filename } = await downloadMeetingDocx(job.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setSaveMessage(`Downloaded "${filename}" with latest saved edits.`)
      setTimeout(() => setSaveMessage(null), 5000)
      refreshSavedDrafts()
    } catch (err: any) {
      setError(err.message || 'Failed to download DOCX.')
    } finally {
      setIsDownloading(null)
    }
  }

  const handleDownloadSavedDocx = async (savedJobId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setIsDownloading(savedJobId)
    try {
      const { blob, filename } = await downloadMeetingDocx(savedJobId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err.message || 'Failed to download DOCX.')
    } finally {
      setIsDownloading(null)
    }
  }

  const handleReopenDraft = (savedJob: MeetingJob) => {
    setJob(savedJob)
    if (savedJob.draft) {
      setDraft(savedJob.draft)
      setMeetingTitle(savedJob.draft.title || 'Institutional Meeting')
    } else {
      setDraft(null)
    }
    if (savedJob.transcript) {
      setTranscriptText(savedJob.transcript)
    }
    localStorage.setItem('synora_active_meeting_job_id', savedJob.id)
    setActiveTab('editor')
    setSaveMessage(`Reopened draft: "${savedJob.draft?.title || 'Saved Draft'}"`)
    setTimeout(() => setSaveMessage(null), 4000)
  }

  return (
    <div className="workspace-flow meeting-flow">
      {/* Navigation tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '16px' }}>
        <button
          type="button"
          className={`button ${activeTab === 'editor' ? 'primary' : 'secondary'}`}
          onClick={() => setActiveTab('editor')}
        >
          Draft Editor
        </button>
        <button
          type="button"
          className={`button ${activeTab === 'saved' ? 'primary' : 'secondary'}`}
          onClick={() => {
            setActiveTab('saved')
            refreshSavedDrafts()
          }}
        >
          Saved Drafts ({savedDrafts.length})
        </button>
      </div>

      {activeTab === 'saved' ? (
        <div className="saved-drafts-panel" style={{ display: 'grid', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h2 style={{ fontSize: '18px', margin: 0 }}>Saved ForumNotes Drafts</h2>
              <p style={{ color: 'var(--muted)', fontSize: '13px', margin: '4px 0 0 0' }}>
                Browse saved drafts, reopen any draft to continue editing, or download the latest formatted DOCX.
              </p>
            </div>
            <button
              type="button"
              className="button secondary"
              disabled={isLoadingSaved}
              onClick={refreshSavedDrafts}
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              {isLoadingSaved ? 'Refreshing…' : '↻ Refresh list'}
            </button>
          </div>

          {savedDrafts.length === 0 ? (
            <div className="draft-card" style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--muted)' }}>
              <p style={{ margin: 0, fontSize: '14px' }}>No saved ForumNotes drafts found.</p>
              <p style={{ margin: '8px 0 16px 0', fontSize: '12px' }}>
                Upload an audio recording or transcript in the Draft Editor, generate minutes, and save your edits to see them listed here.
              </p>
              <button
                type="button"
                className="button primary"
                onClick={() => setActiveTab('editor')}
              >
                Go to Draft Editor
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '12px' }}>
              {savedDrafts.map((item) => {
                const itemTitle = item.draft?.title || 'Untitled Meeting Record'
                const dateStr = item.updatedAt || item.createdAt
                const formattedDate = dateStr
                  ? new Date(dateStr).toLocaleString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Date recorded'

                const topicsCount = item.draft?.discussions?.length ?? 0
                const decsCount = item.draft?.decisions?.length ?? 0
                const actsCount = item.draft?.actionItems?.length ?? 0

                return (
                  <div
                    key={item.id}
                    className="draft-card"
                    style={{
                      display: 'grid',
                      gap: '10px',
                      borderLeft: job?.id === item.id ? '3px solid var(--accent, #6366f1)' : undefined,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
                      <div style={{ flex: 1, minWidth: '220px' }}>
                        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{itemTitle}</h3>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', marginTop: '6px' }}>
                          <span style={{ fontSize: '12px', color: 'var(--muted)' }}>
                            📅 {formattedDate}
                          </span>
                          <span className="citation-badge" style={{ fontSize: '11px' }}>
                            {item.source === 'audio' ? `🎙 ${item.audioFileName || 'Audio'}` : '📄 Transcript'}
                          </span>
                          {job?.id === item.id && (
                            <span className="draft-badge" style={{ fontSize: '11px', background: '#312e81', color: '#c7d2fe' }}>
                              Active in Editor
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                        <button
                          type="button"
                          className="button secondary"
                          disabled={isDownloading === item.id}
                          onClick={(e) => handleDownloadSavedDocx(item.id, e)}
                          style={{ fontSize: '12px', padding: '6px 12px' }}
                        >
                          {isDownloading === item.id ? 'Downloading…' : '⬇ Download DOCX'}
                        </button>
                        <button
                          type="button"
                          className="button primary"
                          onClick={() => handleReopenDraft(item)}
                          style={{ fontSize: '12px', padding: '6px 12px' }}
                        >
                          Reopen & Edit
                        </button>
                      </div>
                    </div>

                    {item.draft?.summary && (
                      <p style={{ margin: 0, fontSize: '13px', color: 'var(--sub)', lineHeight: '1.4' }}>
                        {item.draft.summary.length > 200 ? `${item.draft.summary.slice(0, 200)}…` : item.draft.summary}
                      </p>
                    )}

                    <div style={{ display: 'flex', gap: '14px', fontSize: '12px', color: 'var(--muted)', borderTop: '1px solid var(--border)', paddingTop: '8px', flexWrap: 'wrap' }}>
                      <span><b>{topicsCount}</b> discussion topics</span>
                      <span>•</span>
                      <span><b>{decsCount}</b> decisions</span>
                      <span>•</span>
                      <span><b>{actsCount}</b> action items</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ) : (
        <>
          <label className="field">
            Meeting Title
            <input
              value={draft ? draft.title : meetingTitle}
              onChange={(e) => {
                const val = e.target.value
                setMeetingTitle(val)
                if (draft) {
                  setDraft({ ...draft, title: val })
                }
              }}
              placeholder="e.g. Academic Council Annual Meeting"
            />
          </label>

          <FileQueue
            title="Upload audio recording"
            accept={['.mp3', '.wav', '.m4a']}
            files={audioFiles}
            onChange={(files) => {
              setAudioFiles(files)
              setJob(null)
            }}
            hint="MP3, WAV, or M4A · up to 200 MB each"
            maxMb={200}
          />
          <FileQueue
            title="Upload transcript"
            accept={['.txt', '.docx', '.pdf', '.vtt', '.srt']}
            files={transcriptFiles}
            onChange={(files) => {
              setTranscriptFiles(files)
              setJob(null)
            }}
            hint="TXT, DOCX, PDF, VTT, or SRT · up to 20 MB each"
          />
          <p className="integration-state">
            {draft
              ? 'ForumNotes generated. Review decisions and verify flagged action item owners and deadlines.'
              : 'Use audio, a transcript, or both. Transcribe audio locally with Whisper, inspect and edit proceedings, and generate verifiable draft minutes.'}
          </p>
          {error && <div className="status-banner error" role="alert">{error}</div>}
          {statusMessage && (
            <div className="status-indicator">
              <div className="spinner" />
              <span>{statusMessage}</span>
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '4px' }}>
            {audioFiles.length > 0 && (
              <button
                type="button"
                className="button secondary"
                disabled={isTranscribing || isLoading}
                onClick={handleTranscribeAudio}
              >
                {isTranscribing ? 'Transcribing audio…' : 'Transcribe audio recording'}
              </button>
            )}
            <button
              type="button"
              className="button primary"
              disabled={(!audioFiles.length && !transcriptFiles.length && !transcriptText.trim()) || isLoading || isTranscribing}
              onClick={handleGenerate}
            >
              {isLoading ? 'Generating draft minutes…' : 'Generate draft minutes'}
            </button>
          </div>

          <div className="draft-card" style={{ marginTop: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h3 style={{ margin: 0 }}>Meeting Transcript (Review & Edit)</h3>
              {transcriptText && (
                <span style={{ fontSize: '12px', color: 'var(--muted)' }}>
                  {transcriptText.split('\n').filter(Boolean).length} segments · {transcriptText.length} characters
                </span>
              )}
            </div>
            <p style={{ fontSize: '13px', color: 'var(--muted)', marginTop: 0, marginBottom: '8px' }}>
              Transcribed speech with segment timestamps [MM:SS] appears here. You can review, correct terms or speaker names, and generate or regenerate minutes from your edits.
            </p>
            <textarea
              className="field"
              style={{ minHeight: '140px', fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.5', width: '100%', boxSizing: 'border-box' }}
              value={transcriptText}
              onChange={(e) => setTranscriptText(e.target.value)}
              placeholder="Transcribed audio or extracted transcript text will appear here with segment timestamps [MM:SS]. You can also paste or type dialogue directly here..."
              disabled={isTranscribing || isLoading}
            />
            {transcriptText.trim() && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  className="button primary"
                  disabled={isLoading || isTranscribing}
                  onClick={handleGenerate}
                >
                  {isLoading ? 'Regenerating minutes…' : 'Regenerate minutes from edited transcript'}
                </button>
              </div>
            )}
          </div>

          <section className="minutes-draft">
            <b>Reviewable minutes draft</b>
            {!draft && !isLoading && (
              <p>A generated draft will remain editable and will identify uncertain decisions, owners, and deadlines for review.</p>
            )}
            {draft && (
              <div className="draft-container">
                <div className="status-banner warning">
                  {job?.limitations?.[0] || 'Generated draft requires human review. Action owners and deadlines are included only when explicitly stated in source.'}
                </div>

                <div className="draft-card">
                  <h3>Draft Title & Summary</h3>
                  <input
                    className="field"
                    style={{ marginBottom: '12px', fontWeight: 600 }}
                    value={draft.title}
                    onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  />
                  <textarea
                    className="field"
                    style={{ minHeight: '90px' }}
                    value={draft.summary}
                    onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
                  />
                </div>

                <div className="draft-card">
                  <h3>Discussion Topics ({draft.discussions.length})</h3>
                  {draft.discussions.length === 0 ? (
                    <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
                      No explicit discussion topics identified in the transcript.
                    </p>
                  ) : (
                    draft.discussions.map((d, i) => (
                      <div key={i} className="draft-item" style={{ marginBottom: '10px' }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '6px' }}>
                          <input
                            className="field"
                            style={{ fontWeight: 600, fontSize: '13px', marginBottom: 0, padding: '4px 8px', flex: 1 }}
                            value={d.topic}
                            onChange={(e) => {
                              const next = [...draft.discussions]
                              next[i] = { ...d, topic: e.target.value }
                              setDraft({ ...draft, discussions: next })
                            }}
                          />
                          {d.timestamp && <span className="citation-badge">{d.timestamp}</span>}
                        </div>
                        <div style={{ display: 'grid', gap: '4px', paddingLeft: '12px' }}>
                          {d.points.map((pt, j) => (
                            <textarea
                              key={j}
                              className="field"
                              style={{ minHeight: '36px', fontSize: '12px', margin: 0, padding: '4px 8px', color: 'var(--sub)' }}
                              value={pt}
                              onChange={(e) => {
                                const next = [...draft.discussions]
                                const nextPts = [...d.points]
                                nextPts[j] = e.target.value
                                next[i] = { ...d, points: nextPts }
                                setDraft({ ...draft, discussions: next })
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <div className="draft-card">
                  <h3>Formal Decisions ({draft.decisions.length})</h3>
                  {draft.decisions.length === 0 ? (
                    <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
                      No formal resolutions or voting outcomes were explicitly finalized in the recorded segment.
                    </p>
                  ) : (
                    draft.decisions.map((dec, i) => (
                      <div key={i} className="draft-item" style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '8px', alignItems: 'center' }}>
                        <input
                          className="field"
                          style={{ fontSize: '13px', padding: '6px 8px', marginBottom: 0 }}
                          value={dec.decision}
                          onChange={(e) => {
                            const next = [...draft.decisions]
                            next[i] = { ...dec, decision: e.target.value }
                            setDraft({ ...draft, decisions: next })
                          }}
                        />
                        <select
                          style={{ fontSize: '12px', padding: '6px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg)' }}
                          value={dec.status}
                          onChange={(e) => {
                            const next = [...draft.decisions]
                            next[i] = { ...dec, status: e.target.value as 'agreed' | 'pending' }
                            setDraft({ ...draft, decisions: next })
                          }}
                        >
                          <option value="agreed">agreed</option>
                          <option value="pending">pending</option>
                        </select>
                      </div>
                    ))
                  )}
                </div>

                <div className="draft-card">
                  <h3>Action Items ({draft.actionItems.length})</h3>
                  {draft.actionItems.length === 0 ? (
                    <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
                      No explicit action assignments or task commitments were identified in the source.
                    </p>
                  ) : (
                    draft.actionItems.map((act, i) => (
                      <div key={i} className="draft-item" style={{ display: 'grid', gap: '8px' }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <input
                            className="field"
                            style={{ flex: 1, fontSize: '13px', padding: '6px 8px', marginBottom: 0 }}
                            value={act.task}
                            onChange={(e) => {
                              const next = [...draft.actionItems]
                              next[i] = { ...act, task: e.target.value }
                              setDraft({ ...draft, actionItems: next })
                            }}
                          />
                          {act.uncertain && <span className="draft-badge uncertain">Uncertain</span>}
                        </div>
                        <div className="two-up" style={{ marginBottom: 0 }}>
                          <input
                            style={{ fontSize: '12px', padding: '6px 8px' }}
                            placeholder="Owner (optional)"
                            value={act.owner || ''}
                            onChange={(e) => {
                              const next = [...draft.actionItems]
                              next[i] = { ...act, owner: e.target.value || null, uncertain: !e.target.value || !act.dueDate }
                              setDraft({ ...draft, actionItems: next })
                            }}
                          />
                          <input
                            style={{ fontSize: '12px', padding: '6px 8px' }}
                            placeholder="Due Date (optional)"
                            value={act.dueDate || ''}
                            onChange={(e) => {
                              const next = [...draft.actionItems]
                              next[i] = { ...act, dueDate: e.target.value || null, uncertain: !act.owner || !e.target.value }
                              setDraft({ ...draft, actionItems: next })
                            }}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {draft.uncertainties.length > 0 && (
                  <div className="uncertainty-box">
                    <b style={{ display: 'block', marginBottom: '6px' }}>Identified Source Uncertainties</b>
                    <div style={{ display: 'grid', gap: '4px' }}>
                      {draft.uncertainties.map((u, i) => (
                        <input
                          key={i}
                          className="field"
                          style={{ fontSize: '12px', padding: '4px 8px', marginBottom: 0 }}
                          value={u}
                          onChange={(e) => {
                            const next = [...draft.uncertainties]
                            next[i] = e.target.value
                            setDraft({ ...draft, uncertainties: next })
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: '16px', display: 'grid', gap: '8px' }}>
                  {saveMessage && (
                    <div className="status-banner success" role="status" style={{ margin: 0 }}>
                      ✓ {saveMessage}
                    </div>
                  )}
                  {saveError && (
                    <div className="status-banner error" role="alert" style={{ margin: 0 }}>
                      ⚠ {saveError}
                    </div>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="button primary"
                        disabled={isSaving || isDownloading === 'current'}
                        onClick={handleSaveDraft}
                      >
                        {isSaving ? 'Saving edits…' : 'Save draft edits'}
                      </button>
                      <button
                        type="button"
                        className="button secondary"
                        disabled={isSaving || isDownloading === 'current'}
                        onClick={handleDownloadCurrentDocx}
                      >
                        {isDownloading === 'current' ? 'Generating DOCX…' : '⬇ Download formatted DOCX'}
                      </button>
                    </div>
                    {savedDrafts.length > 0 && (
                      <button
                        type="button"
                        className="button secondary"
                        onClick={() => {
                          setActiveTab('saved')
                          refreshSavedDrafts()
                        }}
                        style={{ fontSize: '12px' }}
                      >
                        Browse all saved drafts ({savedDrafts.length}) →
                      </button>
                    )}
                  </div>
                </div>

              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}

function Workspace({ module }: { module: ModuleDefinition }) {
  const [notice, setNotice] = useState<string>()
  const unavailable = (task: string) => setNotice(`${task} requires a configured server-side provider. No file was uploaded or processed.`)
  const documentTypes = ['.pdf', '.docx', '.txt']
  const [earlierFiles, setEarlierFiles] = useState<LocalFile[]>([])
  const [revisedFiles, setRevisedFiles] = useState<LocalFile[]>([])
  const [shieldFiles, setShieldFiles] = useState<LocalFile[]>([])

  let body = null
  if (module.id === 'change') {
    body = (
      <div className="workspace-flow">
        <div className="two-up">
          <FileQueue title="Earlier version" accept={documentTypes} files={earlierFiles} onChange={setEarlierFiles} multiple={false} hint="PDF, DOCX, or TXT · up to 20 MB" />
          <FileQueue title="Revised version" accept={documentTypes} files={revisedFiles} onChange={setRevisedFiles} multiple={false} hint="PDF, DOCX, or TXT · up to 20 MB" />
        </div>
        <button className="button primary" disabled={!earlierFiles.length || !revisedFiles.length} onClick={() => unavailable('Document comparison')}>
          Compare versions
        </button>
      </div>
    )
  } else if (module.id === 'shield') {
    body = (
      <div className="workspace-flow">
        <FileQueue title="Private document" accept={documentTypes} files={shieldFiles} onChange={setShieldFiles} multiple={false} hint="PDF, DOCX, or TXT · up to 20 MB" />
        <button className="button primary" disabled={!shieldFiles.length} onClick={() => unavailable('Privacy scanning')}>
          Inspect content
        </button>
      </div>
    )
  } else if (module.id === 'rag') {
    body = <RagWorkspace />
  } else if (module.id === 'translate') {
    body = <TranslateWorkspace />
  } else if (module.id === 'meeting') {
    body = <MeetingWorkspace />
  }

  return (
    <main className="app-page content">
      <header className="page-header">
        <p className="eyebrow">{module.name} · Independent workspace</p>
        <h1>{module.workspaceTitle}</h1>
        <p className="lede">{module.workspaceDescription}</p>
      </header>
      <section className="workspace-panel">
        <h2>
          {module.id === 'rag'
            ? 'Document-grounded collection'
            : module.id === 'translate'
            ? 'Institutional document translation'
            : module.id === 'meeting'
            ? 'Source to reviewable minutes'
            : 'Main input'}
        </h2>
        <p>
          {module.id === 'rag' || module.id === 'translate' || module.id === 'meeting'
            ? 'Connected to local institutional intelligence service.'
            : 'Local file selection is available. Secure upload and live processing are configured separately.'}
        </p>
        {body}
        {notice && <p className="notice" role="status">{notice}</p>}
      </section>
    </main>
  )
}


export function App() { const { route, navigate } = useRoute(); const content = route.kind === 'landing' ? <Landing navigate={navigate} /> : route.kind === 'suite' ? <Suite navigate={navigate} /> : route.kind === 'workflow' ? <Workflow module={moduleById(route.id)} navigate={navigate} /> : <Workspace module={moduleById(route.id)} />; return <><BackDock route={route} navigate={navigate} />{content}</> }
