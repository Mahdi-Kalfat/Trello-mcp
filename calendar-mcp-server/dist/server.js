"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const calendarTools_1 = require("./tools/calendarTools");
const calendarToolHandlers_1 = require("./tools/calendarToolHandlers");
const app = (0, express_1.default)();
app.use((0, cors_1.default)());
app.use(express_1.default.json());
// SSE endpoint for MCP
app.get('/sse', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    // Send session ID
    const sessionId = Math.random().toString(36).substring(2);
    res.write(`data: session_id=${sessionId}\n\n`);
    // Send tools list
    res.write(`data: ${JSON.stringify({ tools: calendarTools_1.calendarTools })}\n\n`);
    // Keep connection alive
    const keepAlive = setInterval(() => {
        res.write('data: keep-alive\n\n');
    }, 15000);
    req.on('close', () => {
        clearInterval(keepAlive);
        res.end();
    });
});
// Message endpoint to handle tool calls
app.post('/messages', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const { session_id, content } = req.body;
    if (!session_id || !content || !content.tool_calls) {
        return res.status(400).json({ error: 'Invalid request' });
    }
    const toolCalls = content.tool_calls;
    const results = [];
    for (const toolCall of toolCalls) {
        const handler = calendarToolHandlers_1.calendarToolHandlers[toolCall.name];
        if (!handler) {
            results.push({ error: `Tool ${toolCall.name} not found` });
            continue;
        }
        try {
            const result = yield handler(toolCall.arguments);
            results.push({ tool: toolCall.name, result });
        }
        catch (error) {
            results.push({ tool: toolCall.name, error: error.message });
        }
    }
    res.json({ results });
}));
exports.default = app;
