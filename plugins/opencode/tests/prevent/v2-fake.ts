/**
 * A stand-in for the OpenCode v2 plugin context (`Plugin.Context` from @opencode/plugin):
 * only the domains the toolkit uses. It records hook registrations and MCP transforms,
 * serves canned session messages, and lets a test push server events.
 *
 * Imports use explicit extensions so Node can load this file too (tests/node-smoke.ts).
 */

type Hook = (event: any) => unknown;

export type FakeOptions = {
  directory: string;
  /** What `session.context` returns, per session. */
  messages?: Record<string, unknown[]>;
  /** Parent of each child session. */
  parents?: Record<string, string>;
  /** Make `session.synthetic` reject. */
  syntheticFails?: boolean;
};

export function createFakeContext(options: FakeOptions) {
  const toolHooks = new Map<string, Hook>();
  const sessionHooks = new Map<string, Hook>();
  const mcpTransforms: Array<(editor: any) => void> = [];
  const synthetic: any[] = [];
  const contextCalls: string[] = [];
  const subscribers = new Set<{ push: (event: any) => void; types?: Set<string> }>();

  const ctx = {
    location: { directory: options.directory },
    tool: {
      hook: async (name: string, callback: Hook) => {
        toolHooks.set(name, callback);
        return { dispose: async () => void toolHooks.delete(name) };
      },
    },
    session: {
      hook: async (name: string, callback: Hook) => {
        sessionHooks.set(name, callback);
        return { dispose: async () => void sessionHooks.delete(name) };
      },
      context: async ({ sessionID }: { sessionID: string }) => {
        contextCalls.push(sessionID);
        return options.messages?.[sessionID] ?? [];
      },
      synthetic: async (input: any) => {
        if (options.syntheticFails) throw new Error("admission failed");
        synthetic.push(input);
        return {};
      },
      get: async ({ sessionID }: { sessionID: string }) => ({
        id: sessionID,
        ...(options.parents?.[sessionID] ? { parentID: options.parents[sessionID] } : {}),
      }),
    },
    mcp: {
      transform: async (callback: (editor: any) => void) => {
        mcpTransforms.push(callback);
        return { dispose: async () => {} };
      },
    },
    event: {
      subscribe: (opts?: { types?: string[]; signal?: AbortSignal }) => {
        const queue: any[] = [];
        let wake: (() => void) | null = null;
        const sub = {
          types: opts?.types?.length ? new Set(opts.types) : undefined,
          push: (event: any) => {
            queue.push(event);
            wake?.();
          },
        };
        subscribers.add(sub);
        const aborted = () => opts?.signal?.aborted === true;
        opts?.signal?.addEventListener("abort", () => {
          subscribers.delete(sub);
          wake?.();
        });
        return {
          async *[Symbol.asyncIterator]() {
            while (!aborted()) {
              if (queue.length === 0) await new Promise<void>((r) => (wake = r));
              wake = null;
              while (queue.length > 0 && !aborted()) yield queue.shift();
            }
          },
        };
      },
    },
  };

  /** Run the MCP transforms against a config map, the way OpenCode's editor applies them. */
  function applyMcp(servers: Record<string, any>) {
    const editor = {
      list: () => Object.entries(servers),
      get: (name: string) => servers[name],
      set: (name: string, config: any) => void (servers[name] = config),
      update: (name: string, update: (config: any) => void) => {
        if (servers[name]) update(servers[name]);
      },
      remove: (name: string) => void delete servers[name],
    };
    for (const transform of mcpTransforms) transform(editor);
    return servers;
  }

  /** Deliver a server event to every matching subscriber, then let the loops run. */
  async function emit(event: any) {
    for (const sub of subscribers) {
      if (!sub.types || sub.types.has(event.type)) sub.push(event);
    }
    await new Promise((r) => setTimeout(r, 5));
  }

  return {
    ctx,
    toolHooks,
    sessionHooks,
    synthetic,
    contextCalls,
    subscriberCount: () => subscribers.size,
    applyMcp,
    emit,
    before: (event: any) => toolHooks.get("execute.before")!(event),
    after: (event: any) => toolHooks.get("execute.after")!(event),
    idle: (event: any) => sessionHooks.get("experimental.idle")!(event),
  };
}
