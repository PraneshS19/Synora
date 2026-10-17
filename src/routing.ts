import { useEffect, useState } from 'react'
import type { ModuleId } from './modules'

export type Route = { kind: 'landing' } | { kind: 'suite' } | { kind: 'workflow'; id: ModuleId } | { kind: 'workspace'; id: ModuleId }

const ids: ModuleId[] = ['change', 'rag', 'shield', 'translate', 'meeting']
const parse = (hash = window.location.hash): Route => {
  const value = hash.replace(/^#\/?/, '')
  if (value === 'suite') return { kind: 'suite' }
  const match = value.match(/^(change|rag|shield|translate|meeting)\/(workflow|workspace)$/)
  if (match && ids.includes(match[1] as ModuleId)) return { kind: match[2] === 'workflow' ? 'workflow' : 'workspace', id: match[1] as ModuleId }
  return { kind: 'landing' }
}

export const href = (route: Route) => route.kind === 'landing' ? '#/' : route.kind === 'suite' ? '#/suite' : `#/${route.id}/${route.kind}`

export function useRoute() {
  const [route, setRoute] = useState<Route>(() => parse())
  useEffect(() => { const onHash = () => setRoute(parse()); addEventListener('hashchange', onHash); return () => removeEventListener('hashchange', onHash) }, [])
  const navigate = (next: Route) => { window.location.hash = href(next) }
  return { route, navigate }
}
