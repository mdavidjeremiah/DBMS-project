import { useSyncExternalStore } from "react"

const subscribe = () => () => {}

/**
 * Detects whether the component has mounted on the client, without the
 * classic `useEffect(() => setMounted(true), [])` pattern -- that pattern
 * trips the `react-hooks/set-state-in-effect` lint rule (setState called
 * synchronously inside an effect body), which this project's ESLint config
 * treats as an error, not a warning, so it fails `next build`.
 *
 * useSyncExternalStore sidesteps this cleanly: the server snapshot is
 * always `false`, the client snapshot is always `true`, and React handles
 * reconciling the difference on hydration for us instead of us doing it by
 * hand with an effect.
 */
export function useHasMounted() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false
  )
}