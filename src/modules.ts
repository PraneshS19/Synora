export type ModuleId = 'change' | 'rag' | 'shield' | 'translate' | 'meeting'

export type ModuleDefinition = {
  id: ModuleId
  number: string
  name: string
  eyebrow: string
  landingTitle: string
  landingDescription: string
  workflowTitle: string
  workflowHeading: string
  workflowDescription: string
  workspaceTitle: string
  workspaceDescription: string
  steps: Array<{ title: string; description: string }>
}

export const modules: ModuleDefinition[] = [
  {
    id: 'change', number: '01', name: 'ChangeLens', eyebrow: 'Intelligent document change detection',
    landingTitle: 'Every change.\nMade clear.', landingDescription: 'Compare policy and circular versions to understand what changed and what needs attention.',
    workflowTitle: 'Version comparison workflow', workflowHeading: 'Every revision,\nin context.', workflowDescription: 'See the path from two document versions to a reviewable comparison—without changing either original.',
    workspaceTitle: 'Compare document versions.', workspaceDescription: 'Add two text-based versions and keep observed changes separate from any future impact review.',
    steps: [{ title: 'Add versions', description: 'Choose two policy or circular versions.' }, { title: 'Compare passages', description: 'Observe additions, removals, and edits.' }, { title: 'Review changes', description: 'Classify findings before reporting.' }],
  },
  {
    id: 'rag', number: '02', name: 'Institutional RAG', eyebrow: 'Document-based AI assistant',
    landingTitle: 'Answers grounded\nin your knowledge.', landingDescription: 'Ask questions across a private document collection and explore answers grounded in available sources.',
    workflowTitle: 'Grounded answer workflow', workflowHeading: 'Knowledge in.\nGrounded answers out.', workflowDescription: 'Explore a private document collection through questions and answers grounded in available sources.',
    workspaceTitle: 'Ask your documents.', workspaceDescription: 'Create collections and inspect evidence before relying on an answer.',
    steps: [{ title: 'Private collection', description: 'Create a collection for this workspace.' }, { title: 'Ask a question', description: 'Enter a question for available evidence.' }, { title: 'Find context', description: 'Retrieve relevant passages when configured.' }, { title: 'Review answer', description: 'Inspect support before relying on it.' }],
  },
  {
    id: 'shield', number: '03', name: 'IndicShield', eyebrow: 'Sensitive information detection',
    landingTitle: 'Sensitive information.\nClearly in view.', landingDescription: 'Identify and review sensitive information with a workflow designed for clarity and control.',
    workflowTitle: 'Sensitive information workflow', workflowHeading: 'Sensitive information.\nIn clear view.', workflowDescription: 'Identify potentially sensitive content and review findings through a clear, controlled workflow.',
    workspaceTitle: 'Review sensitive information.', workspaceDescription: 'Provide supported content, inspect reviewable findings, and understand redaction limitations.',
    steps: [{ title: 'Provide content', description: 'Keep the source private in this workspace.' }, { title: 'Inspect content', description: 'Analyze supported content when configured.' }, { title: 'Review findings', description: 'Select, dismiss, or mark a finding.' }, { title: 'Review and proceed', description: 'Confirm handling before you continue.' }],
  },
  {
    id: 'translate', number: '04', name: 'IndicTranslate', eyebrow: 'Reviewable language drafts',
    landingTitle: 'Across languages.\nWith clarity.', landingDescription: 'Create Indian-language drafts designed to be reviewed and refined before use.',
    workflowTitle: 'Translation draft workflow', workflowHeading: 'Meaning preserved.\nAcross languages.', workflowDescription: 'Create Indian-language drafts that can be reviewed and refined before use.',
    workspaceTitle: 'Translate with review built in.', workspaceDescription: 'Create editable drafts without changing the original or publishing automatically.',
    steps: [{ title: 'Source text', description: 'Start with text you want to translate.' }, { title: 'Select language', description: 'Choose a supported target language.' }, { title: 'Generate draft', description: 'Create a draft when configured.' }, { title: 'Review the draft', description: 'Edit and refine before use.' }],
  },
  {
    id: 'meeting', number: '05', name: 'ForumNotes', eyebrow: 'Meeting intelligence',
    landingTitle: 'Conversations into\nclear outcomes.', landingDescription: 'Turn meeting content into structured minutes, decisions and action items that can be reviewed.',
    workflowTitle: 'Meeting record workflow', workflowHeading: 'From discussion\nto decisions.', workflowDescription: 'Turn meeting content into structured minutes, decisions and action items that can be reviewed.',
    workspaceTitle: 'Capture reviewable minutes.', workspaceDescription: 'Add a transcript or recording source and confirm incomplete details before finalization.',
    steps: [{ title: 'Meeting content', description: 'Add a recording or transcript.' }, { title: 'Organize key points', description: 'Structure discussion from available source.' }, { title: 'Draft minutes', description: 'Create a reviewable draft.' }, { title: 'Review minutes', description: 'Confirm incomplete details.' }],
  },
]

export const moduleById = (id: ModuleId) => modules.find((module) => module.id === id)!
