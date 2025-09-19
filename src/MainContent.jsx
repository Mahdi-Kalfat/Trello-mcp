import { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon, ChevronDoubleDownIcon, UserIcon, CpuChipIcon } from '@heroicons/react/24/solid';

export default function MainContent({ messages, sessionId }) {
  const [input, setInput] = useState('');
  const [showScrollArrow, setShowScrollArrow] = useState(false);
  const chatRef = useRef(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [aiTyping, setAiTyping] = useState("");

  useEffect(() => {
    const chatEl = chatRef.current;
    if (!chatEl) return;
    const handleScroll = () => {
      const atBottom = chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight < 5;
      setShowScrollArrow(!atBottom);
    };
    chatEl.addEventListener('scroll', handleScroll);
    // Initial check
    handleScroll();
    return () => chatEl.removeEventListener('scroll', handleScroll);
  }, [messages]);

  const scrollToBottom = () => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
      setShowScrollArrow(false);
    }
  };

  // handleSend can be updated to persist messages if needed
  const handleSend = async () => {
    if (window.updateActivity) window.updateActivity();
    if (!input.trim()) return;
    setInput('');
    setLoadingAI(true);
    setAiTyping("");
    // Add user message to messages
    const userMsg = {
      sender: 'user',
      text: input,
      time: new Date().toISOString()
    };
    let newMessages = [...messages, userMsg];
    // Show AI typing animation until response
    setAiTyping('');
    setLoadingAI(true);
    // Send to LLM agent
    try {
      const sendObj = { prompt: input, session_id: sessionId };
      console.log('Sending to LLM agent:', sendObj);
      const res = await fetch('http://localhost:8001/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sendObj)
      });
      const data = await res.json();
      setLoadingAI(false);
      setAiTyping("");
      // Add AI response to messages
      if (data && data.response) {
        const aiMsg = {
          sender: 'ai',
          text: data.response,
          time: new Date().toISOString()
        };
        newMessages = [...newMessages, aiMsg];
      }
      // Update messages
      if (typeof window !== 'undefined' && window.setSelectedChatMessages) {
        window.setSelectedChatMessages(newMessages);
      }
    } catch (err) {
      setLoadingAI(false);
      setAiTyping("");
      console.error('Failed to get AI response:', err);
    }
  };

  return (
    <div className="flex flex-1 items-center justify-center min-h-0 h-full w-full bg-black">
      <div className="flex-1 w-full h-full max-w-5xl min-h-[70vh] bg-gradient-to-br from-gray-900 via-black to-gray-800 rounded-3xl shadow-2xl p-8 sm:p-12 flex flex-col gap-8">
        {/* Chat and input area fill card */}
        <div className="flex flex-col flex-1">
          {/* Chat messages with scroll, section is larger to reach textarea, gap added, scrollbar hidden, scroll-to-bottom arrow */}
          <div className="relative flex flex-col gap-3 overflow-y-auto pb-2 custom-chat-scroll" style={{height: 'calc(100vh - 320px)', maxHeight: '600px'}} ref={chatRef}>
            <style>{`
              .custom-chat-scroll::-webkit-scrollbar { display: none; }
              .custom-chat-scroll { scrollbar-width: none; msOverflowStyle: none; }
            `}</style>
            {messages.length === 0 && !loadingAI && !aiTyping ? (
              <div className="flex items-center justify-center h-full w-full">
                <span className="text-lg font-semibold text-white/60">How can I help you today?</span>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`flex flex-col items-${msg.sender === 'ai' ? 'start' : 'end'} mb-2`}>
                  {msg.sender === 'ai' ? (
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-8 h-8 rounded-full border border-white/20 shadow bg-purple-600 flex items-center justify-center">
                        <CpuChipIcon className="h-5 w-5 text-white" />
                      </span>
                      <span className="text-xs font-semibold text-white/80">AI Assistant</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mb-1 flex-row-reverse justify-end">
                      <span className="w-8 h-8 rounded-full border border-white/20 shadow bg-gray-800 flex items-center justify-center">
                        <UserIcon className="h-5 w-5 text-white" />
                      </span>
                      <span className="text-xs font-semibold text-white/80">User</span>
                    </div>
                  )}
                  <div className={`px-4 py-2 rounded-2xl text-base font-medium max-w-[70%] break-words whitespace-pre-line ${msg.sender === 'ai' ? 'bg-purple-600 text-white' : 'bg-white/10 text-white'}`}>
                    {msg.text}
                  </div>
                  {msg.time && (
                    <div className="text-xs text-white/60 mt-1 px-4">
                      {new Date(msg.time).toLocaleString()}
                    </div>
                  )}
                </div>
              ))
            )}
            {/* AI loading animation */}
            {loadingAI && (
              <div className="flex flex-col items-start mb-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-8 h-8 rounded-full border border-white/20 shadow bg-purple-600 flex items-center justify-center">
                    <CpuChipIcon className="h-5 w-5 text-white" />
                  </span>
                  <span className="text-xs font-semibold text-white/80">AI Assistant</span>
                </div>
                <div className="px-4 py-2 rounded-2xl text-base font-medium max-w-[70%] bg-purple-600 text-white flex items-center">
                  <span className="flex gap-1">
                    <span className="animate-bounce">.</span>
                    <span className="animate-bounce delay-150">.</span>
                    <span className="animate-bounce delay-300">.</span>
                  </span>
                </div>
              </div>
            )}
            {/* AI typing animation */}
            {aiTyping && (
              <div className="flex flex-col items-start mb-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-8 h-8 rounded-full border border-white/20 shadow bg-purple-600 flex items-center justify-center">
                    <CpuChipIcon className="h-5 w-5 text-white" />
                  </span>
                  <span className="text-xs font-semibold text-white/80">AI Assistant</span>
                </div>
                <div className="px-4 py-2 rounded-2xl text-base font-medium max-w-[70%] bg-purple-600 text-white flex items-center">
                  {aiTyping}
                </div>
              </div>
            )}
            {showScrollArrow && (
              <button
                onClick={scrollToBottom}
                className="absolute right-4 bottom-4 bg-black/40 hover:bg-purple-600 text-white rounded-full p-2 shadow-lg flex items-center justify-center transition-all duration-150"
                aria-label="Scroll to latest message"
                style={{zIndex: 10}}
              >
                <ChevronDoubleDownIcon className="h-6 w-6" />
              </button>
            )}
          </div>
          {/* Small gap between chat and textarea */}
          <div className="h-3" />
          {/* Text area stays in place, button overlays inside bottom right */}
          <div className="relative w-full flex items-end mt-0">
            <style>{`
              .custom-textarea::-webkit-scrollbar { display: none; }
              .custom-textarea { scrollbar-width: none; msOverflowStyle: none; }
            `}</style>
            <textarea
              className="custom-textarea w-full resize-none bg-black/30 text-white rounded-xl p-4 pr-14 border border-white/10 focus:outline-none focus:ring-2 focus:ring-purple-600 min-h-[56px] max-h-40"
              placeholder="Type your message..."
              value={input}
              onChange={e => setInput(e.target.value)}
              rows={3}
            />
            {input.trim() && (
              <button
                onClick={handleSend}
                className="absolute bottom-6 right-8 bg-purple-600 hover:bg-purple-700 text-white rounded-xl p-3 flex items-center justify-center shadow-lg transition-all duration-150"
                aria-label="Send"
                style={{ zIndex: 2 }}
              >
                <PaperAirplaneIcon className="h-6 w-6" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
