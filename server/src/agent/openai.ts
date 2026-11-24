import { config } from "../lib/config.js";

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: { id: string; type: "function"; function: { name: string; arguments: string } }[];
  tool_call_id?: string;
}
export interface ChatResult { message: ChatMessage; promptTokens: number; completionTokens: number }

/** Chamada real à OpenAI Chat Completions (a chave nunca sai do servidor). */
export async function chatCompletion(messages: ChatMessage[], tools: unknown[]): Promise<ChatResult> {
  if (!config.openaiApiKey) throw new Error("OPENAI_API_KEY não configurada");
  const res = await fetch(`${config.openaiBaseUrl}/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${config.openaiApiKey}` },
    body: JSON.stringify({ model: config.openaiModel, messages, tools, temperature: 0.3, max_tokens: 500 }),
    signal: AbortSignal.timeout(30000),
  });
  if (!res.ok) throw new Error(`OpenAI HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json() as any;
  return {
    message: data.choices[0].message,
    promptTokens: data.usage?.prompt_tokens ?? 0,
    completionTokens: data.usage?.completion_tokens ?? 0,
  };
}

export const costMicroUsd = (pin: number, pout: number) =>
  Math.round(pin * config.costInPerMTok + pout * config.costOutPerMTok); // (tokens/1e6)*USD*1e6
