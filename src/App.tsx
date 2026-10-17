import { useEffect, useLayoutEffect, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import { moduleById, modules, type ModuleDefinition, type ModuleId } from './modules'
import { href, useRoute, type Route } from './routing'

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

function Workspace({ module }: { module: ModuleDefinition }) {
  const [notice, setNotice] = useState<string>(), [earlierFiles, setEarlierFiles] = useState<LocalFile[]>([]), [revisedFiles, setRevisedFiles] = useState<LocalFile[]>([]), [shieldFiles, setShieldFiles] = useState<LocalFile[]>([]), [ragFiles, setRagFiles] = useState<LocalFile[]>([]), [translateFiles, setTranslateFiles] = useState<LocalFile[]>([]), [audioFiles, setAudioFiles] = useState<LocalFile[]>([]), [transcriptFiles, setTranscriptFiles] = useState<LocalFile[]>([])
  const unavailable = (task: string) => setNotice(`${task} requires a configured server-side provider. No file was uploaded or processed.`)
  const documentTypes = ['.pdf', '.docx', '.txt']
  const body = module.id === 'change' ? <div className="workspace-flow"><div className="two-up"><FileQueue title="Earlier version" accept={documentTypes} files={earlierFiles} onChange={setEarlierFiles} multiple={false} hint="PDF, DOCX, or TXT · up to 20 MB" /><FileQueue title="Revised version" accept={documentTypes} files={revisedFiles} onChange={setRevisedFiles} multiple={false} hint="PDF, DOCX, or TXT · up to 20 MB" /></div><button className="button primary" disabled={!earlierFiles.length || !revisedFiles.length} onClick={() => unavailable('Document comparison')}>Compare versions</button></div> : module.id === 'rag' ? <div className="workspace-flow"><label className="field">Collection name<input placeholder="e.g. Admissions policies" /></label><FileQueue title="Add documents to start a collection" accept={documentTypes} files={ragFiles} onChange={setRagFiles} hint="PDF, DOCX, or TXT · up to 20 MB each" /><p className="integration-state">{ragFiles.length ? 'Documents are selected in this browser. Upload, extraction, and indexing require a configured secure service.' : 'Select documents before a collection can be indexed.'}</p><label className="field">Question<textarea placeholder="Ask a question grounded in your collection…" /></label><button className="button primary" disabled={!ragFiles.length} onClick={() => unavailable('Retrieval and answer generation')}>Ask collection</button><section className="evidence-panel"><b>Grounded answer & evidence</b><p>No answer is available until the selected documents have been securely indexed and retrieved.</p></section></div> : module.id === 'shield' ? <div className="workspace-flow"><FileQueue title="Private document" accept={documentTypes} files={shieldFiles} onChange={setShieldFiles} multiple={false} hint="PDF, DOCX, or TXT · up to 20 MB" /><button className="button primary" disabled={!shieldFiles.length} onClick={() => unavailable('Privacy scanning')}>Inspect content</button></div> : module.id === 'translate' ? <div className="workspace-flow"><FileQueue title="Upload institutional document" accept={documentTypes} files={translateFiles} onChange={setTranslateFiles} hint="PDF, DOCX, or TXT · up to 20 MB each" /><div className="two-up"><label className="field">Source language<select defaultValue="English"><option>English</option><option>Tamil</option><option>Hindi</option><option>Telugu</option><option>Kannada</option><option>Malayalam</option></select></label><label className="field">Target language<select defaultValue="Tamil"><option>Tamil</option><option>Hindi</option><option>Telugu</option><option>Kannada</option><option>Malayalam</option><option>Bengali</option><option>Marathi</option></select></label></div><label className="field">Optional source text<textarea placeholder="Paste a short passage only when a document is not available…" /></label><p className="integration-state">Document extraction, language support, translation, review and export remain unavailable until a provider is configured. The original file stays unchanged.</p><button className="button primary" disabled={!translateFiles.length} onClick={() => unavailable('Document translation')}>Extract and translate</button><section className="translation-review"><b>Translation review</b><p>Original and translated content will appear here side by side after real extraction and translation are available.</p></section></div> : <div className="workspace-flow meeting-flow"><FileQueue title="Upload audio recording" accept={['.mp3', '.wav', '.m4a']} files={audioFiles} onChange={setAudioFiles} hint="MP3, WAV, or M4A · up to 200 MB each" maxMb={200} /><FileQueue title="Upload transcript" accept={['.txt', '.docx', '.pdf', '.vtt', '.srt']} files={transcriptFiles} onChange={setTranscriptFiles} hint="TXT, DOCX, PDF, VTT, or SRT · up to 20 MB each" /><p className="integration-state">Use audio, a transcript, or both. Transcription and reconciliation require a configured secure service; no draft minutes will be fabricated.</p><button className="button primary" disabled={!audioFiles.length && !transcriptFiles.length} onClick={() => unavailable('Minutes generation')}>Generate draft minutes</button><section className="minutes-draft"><b>Reviewable minutes draft</b><p>A generated draft will remain editable and will identify uncertain decisions, owners, and deadlines for review.</p></section></div>
  return <main className="app-page content"><header className="page-header"><p className="eyebrow">{module.name} · Independent workspace</p><h1>{module.workspaceTitle}</h1><p className="lede">{module.workspaceDescription}</p></header><section className="workspace-panel"><h2>{module.id === 'rag' ? 'Document-grounded collection' : module.id === 'translate' ? 'Institutional document translation' : module.id === 'meeting' ? 'Source to reviewable minutes' : 'Main input'}</h2><p>Local file selection is available. Secure upload and live processing are configured separately.</p>{body}{notice && <p className="notice" role="status">{notice}</p>}</section></main>
}

export function App() { const { route, navigate } = useRoute(); const content = route.kind === 'landing' ? <Landing navigate={navigate} /> : route.kind === 'suite' ? <Suite navigate={navigate} /> : route.kind === 'workflow' ? <Workflow module={moduleById(route.id)} navigate={navigate} /> : <Workspace module={moduleById(route.id)} />; return <><BackDock route={route} navigate={navigate} />{content}</> }
