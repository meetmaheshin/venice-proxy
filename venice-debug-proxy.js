// venice-proxy-clean.js
// Run example (PowerShell):
// $env:VENICE_API_KEY="wvOH0k..."
// node venice-proxy-clean.js

const express = require('express');
const fetch = require('node-fetch');
const app = express();
app.use(express.json({ limit: '2mb' }));

const VENICE_CHAT_URL = 'https://api.venice.ai/api/v1/chat/completions';
const VENICE_KEY = process.env.VENICE_API_KEY || 'wvOH0kYOVHG7Nqgjd3Ft4nagJztR30fsOLgg5W2TaN';

// Robust sanitizer for assistant text (removes <think> variants, duplicates, and meta)
function sanitizeAssistantText(raw) {
  if (!raw || typeof raw !== 'string') return '';

  console.log('SANITIZE INPUT (len):', raw.length);
  console.log('SANITIZE INPUT (first 200):', raw.substring(0, 200));

  let cleaned = raw;
  
  // Remove <think> blocks completely (including nested and malformed ones)
  cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/gi, '');
  
  // Remove any remaining think tags
  cleaned = cleaned.replace(/<\/?think>/gi, '');
  
  // Basic cleanup
  cleaned = cleaned.replace(/\r/g, '').trim();
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n'); // Max 2 consecutive newlines
  cleaned = cleaned.replace(/[ \t]{2,}/g, ' '); // Max 1 space between words

  console.log('SANITIZE OUTPUT (len):', cleaned.length);
  console.log('SANITIZE OUTPUT (first 200):', cleaned.substring(0, 200));

  return cleaned;
}

// keep only allowed OpenAI-style keys from incoming payload
function sanitizePayload(body) {
  const allowed = {};
  if (body.model) allowed.model = body.model;
  if (body.messages) allowed.messages = body.messages;
  if (typeof body.max_tokens !== 'undefined') allowed.max_tokens = Math.min(body.max_tokens, 500);
  if (typeof body.temperature !== 'undefined') allowed.temperature = body.temperature;
  if (typeof body.top_p !== 'undefined') allowed.top_p = body.top_p;
  if (typeof body.stream !== 'undefined') allowed.stream = body.stream;
  if (typeof body.n !== 'undefined') allowed.n = body.n;
  if (typeof body.stop !== 'undefined') allowed.stop = body.stop;
  return allowed;
}

app.post('/api/v1/chat/completions', async (req, res) => {
  console.log('\n--- INCOMING FROM VAPI ---', new Date().toISOString());
  console.log('Request received! Body keys:', Object.keys(req.body || {}));
  
  try {
    const payload = sanitizePayload(req.body);
    console.log('VAPI requested stream?:', !!req.body.stream, 'payload.stream value:', req.body.stream);
    console.log('SANITIZED PAYLOAD KEYS:', Object.keys(payload));

    // Forward to Venice
    const venResp = await fetch(VENICE_CHAT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${VENICE_KEY}`
      },
      body: JSON.stringify(payload)
    });

    console.log('Venice status:', venResp.status);
    const contentType = venResp.headers.get('content-type') || '';
    console.log('Venice content-type:', contentType);

    // If Venice streams SSE, read full stream and extract deltas safely, then return final JSON to Vapi
    if (contentType.startsWith('text/event-stream')) {
      console.log('CAPTURING FULL SSE STREAM FROM VENICE');

      // Read full stream into buffer
      const chunks = [];
      for await (const c of venResp.body) {
        chunks.push(c);
      }
      const full = Buffer.concat(chunks).toString('utf8');
      console.log('Full stream length:', full.length);
      console.log('Full stream sample (first 1000 chars):', full.substring(0, 1000));
      console.log('Full stream sample (last 1000 chars):', full.substring(full.length - 1000));

      // Extract JSON objects from "data: {...}" SSE lines
      const dataJsons = [];
      const re = /data:\s*(\{[\s\S]*?\})(?:\n|$)/g;
      let m;
      while ((m = re.exec(full)) !== null) {
        dataJsons.push(m[1]);
      }

      // Accumulate textual deltas/messages
      let combined = '';
      for (const js of dataJsons) {
        try {
          const obj = JSON.parse(js);
          const delta = obj?.choices?.[0]?.delta?.content;
          const msg = obj?.choices?.[0]?.message?.content;
          if (delta) combined += delta;
          else if (msg) combined += msg;
        } catch (e) {
          // ignore parse errors for individual JSON parts
        }
      }

      console.log('COMBINED RAW TEXT (first 500 chars):', combined.substring(0, 500));
      console.log('COMBINED RAW TEXT (last 500 chars):', combined.substring(Math.max(0, combined.length - 500)));
      console.log('COMBINED TOTAL LENGTH:', combined.length);

      // --- final sanitize before emitting to Vapi (SSE mode) ---
      let cleaned = sanitizeAssistantText(combined || '');
      console.log('AFTER FIRST SANITIZATION (len):', cleaned.length);
      console.log('AFTER FIRST SANITIZATION (content):', cleaned);
      
      cleaned = cleaned.trim();
      
      console.log('AFTER AGGRESSIVE SANITIZATION (len):', cleaned.length);
      console.log('AFTER AGGRESSIVE SANITIZATION (content):', cleaned);

      console.log('Returning cleaned captured reply (len):', cleaned.length);

      // now emit SSE if client asked for streaming
      if (payload.stream === true) {
        const chunkObj = {
          id: `chatcmpl-${Date.now()}`,
          object: 'chat.completion.chunk',
          created: Math.floor(Date.now() / 1000),
          model: payload.model || 'unknown',
          choices: [{ index: 0, delta: { content: cleaned }, finish_reason: null }]
        };

        res.writeHead(200, {
          'Content-Type': 'text/event-stream; charset=utf-8',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        });

        res.write('data: ' + JSON.stringify(chunkObj) + '\n\n');
        res.write('data: [DONE]\n\n');
        return res.end();
      }

        // otherwise return the usual single JSON
        const out = {
        id: `venice-proxy-${Date.now()}`,
        object: 'chat.completion',
        created: Math.floor(Date.now() / 1000),
        model: payload.model || 'unknown',
        choices: [{ index: 0, message: { role: 'assistant', content: cleaned }, finish_reason: 'stop' }],
        usage: {}
        };
        return res.status(200).json(out);


            console.log('RETURNING CLEANED (len):', cleaned.length);
            return res.status(200).json(out);
            }

    // Non-streaming path: parse standard JSON and sanitize
    let venJson = null;
    try {
      venJson = await venResp.json();
    } catch (e) {
      console.error('Failed to parse Venice non-streaming JSON:', e);
    }

    let assistantText = '';
    if (venJson) {
      assistantText = venJson?.choices?.[0]?.message?.content || venJson?.choices?.[0]?.text || '';
    }

    assistantText = assistantText.replace(/<\s*t[hhnk]{2,4}\s*>[\s\S]*?<\s*\/\s*t[hhnk]{2,4}\s*>/gi, '');
    assistantText = assistantText.replace(/<\s*\/?\s*t[hhnk]{2,4}\s*>/gi, '');

    let cleaned = sanitizeAssistantText(assistantText || '');
    console.log('NON-SSE AFTER FIRST SANITIZATION (len):', cleaned.length);
    console.log('NON-SSE AFTER FIRST SANITIZATION (content):', cleaned);
    
    cleaned = cleaned.trim();
    
    console.log('NON-SSE AFTER AGGRESSIVE SANITIZATION (len):', cleaned.length);
    console.log('NON-SSE AFTER AGGRESSIVE SANITIZATION (content):', cleaned);

    const out = {
      id: `venice-proxy-${Date.now()}`,
      object: 'chat.completion',
      created: Math.floor(Date.now() / 1000),
      model: payload.model || 'unknown',
      choices: [ { index: 0, message: { role: 'assistant', content: cleaned }, finish_reason: 'stop' } ],
      usage: {}
    };

    console.log('RETURNING CLEANED (non-stream) len:', cleaned.length);
    res.status(200).json(out);

  } catch (err) {
    console.error('PROXY ERROR:', err && err.stack ? err.stack : err);
    res.status(502).json({ error: 'proxy_error', detail: String(err) });
  }
});

const port = process.env.PORT || 8080;
app.listen(port, () => console.log(`Venice clean proxy listening on :${port}`));
