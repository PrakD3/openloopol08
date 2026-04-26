import { config } from '@/lib/config';
import { type NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const body = (await req.json()) as { text: string; targetLang: string };
  const { text, targetLang } = body;

  if (config.isOffline) {
    try {
      const response = await fetch(
        `${process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434'}/api/generate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'llama3.1:8b',
            prompt: `Translate the following text to ${targetLang}. Return only the translation, no explanation:\n\n${text}`,
            stream: false,
          }),
        }
      );
      const data = (await response.json()) as { response: string };
      return NextResponse.json({ translated: data.response });
    } catch {
      return NextResponse.json({ translated: text });
    }
  }

  try {
    const groqKey = process.env.GROQ_API_KEY;
    if (!groqKey) {
      return NextResponse.json({ translated: text });
    }

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${groqKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'llama-3.1-8b-instant',
        messages: [
          {
            role: 'user',
            content: `Translate the following text to ${targetLang}. Return only the translation:\n\n${text}`,
          },
        ],
      }),
    });

    const data = (await response.json()) as { choices: Array<{ message: { content: string } }> };
    return NextResponse.json({ translated: data.choices[0]?.message?.content ?? text });
  } catch {
    return NextResponse.json({ translated: text });
  }
}
