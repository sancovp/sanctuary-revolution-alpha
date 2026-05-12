/* ═══════════════════════════════════════════════════════════
   Event Bus — In-process pub/sub for SaaS → Frontend push
   
   When /api/cb processes a command, it publishes the result.
   Connected SSE clients (frontends) receive the result.
   
   Uses globalThis to survive Next.js module reloading / HMR.
   ═══════════════════════════════════════════════════════════ */

type Listener = (data: Record<string, unknown>) => void;

class EventBus {
    private listeners = new Set<Listener>();

    subscribe(listener: Listener): () => void {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    publish(data: Record<string, unknown>): void {
        for (const listener of this.listeners) {
            try { listener(data); } catch { /* don't let one listener break others */ }
        }
    }

    get subscriberCount(): number {
        return this.listeners.size;
    }
}

// Survive Next.js HMR and module reloading
const globalForEventBus = globalThis as unknown as { __cbEventBus?: EventBus };
if (!globalForEventBus.__cbEventBus) {
    globalForEventBus.__cbEventBus = new EventBus();
}

/** Singleton event bus — shared across ALL API routes in the same process */
export const cbEventBus: EventBus = globalForEventBus.__cbEventBus;
