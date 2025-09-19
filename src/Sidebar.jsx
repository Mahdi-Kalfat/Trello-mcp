import { useEffect, useState, useRef } from 'react';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  UsersIcon,
  FolderIcon,
  CalendarIcon,
  InboxIcon,
  ChartBarIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowUpRightIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'New Chat', href: '#', icon: PlusIcon },
  { name: 'Search Chats', href: '#', icon: MagnifyingGlassIcon },
  { name: 'Library', href: '#', icon: FolderIcon },
  { name: 'Calendar', href: '/calendar', icon: CalendarIcon },
]

export default function Sidebar({ expanded, setExpanded, selectedChatId, setSelectedChatId, chatHistory, setChatHistory, setSelectedChatMessages, user, setUser }) {
  function classNames(...classes) {
    return classes.filter(Boolean).join(' ')
  }

  // ...existing code...

  useEffect(() => {
    fetch('http://localhost:3001/api/chats')
      .then(res => res.json())
      .then(data => {
        // Each session: { _id, messages: [{ sender, text }], time }
        const history = data.map(chat => ({
          session_id: chat.session_id,
          title: chat.messages.find(m => m.sender === 'user')?.text || 'Untitled Chat',
          time: chat.time,
          messages: chat.messages
        }));
  setChatHistory(history);
  console.log('Loaded chatHistory session_ids:', history.map(chat => chat.session_id));
      });
  }, []);

  // Utility to set cookie
  function setCookie(name, value, minutes) {
    const expires = new Date(Date.now() + minutes * 60 * 1000).toUTCString();
    document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
  }
  // Utility to remove cookie
  function removeCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  }
  // Utility to get cookie
  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }

  // ...existing code...

  // Refresh token cookie on activity
  function refreshTokenCookie() {
    const token = getCookie('user_token');
    if (token) setCookie('user_token', token, 30);
  }

  // Call refreshTokenCookie on user activity
  useEffect(() => {
    window.updateActivity = () => {
      refreshTokenCookie();
    };
  }, []);

  return (
  <div className={`fixed md:static top-0 left-0 h-screen z-40 flex flex-col bg-gradient-to-b from-black via-gray-900 to-black/80 backdrop-blur-lg shadow-[0_4px_32px_0_rgba(255,255,255,0.10)] text-white ${expanded ? 'w-80' : 'w-16'} transition-all duration-300 md:h-screen md:block border-r border-white/10`}>
      <div className="flex items-center h-16 px-4 font-bold text-lg border-b border-white/10 justify-between">
        <span className={`${!expanded && 'hidden'} transition-all duration-300 tracking-wide`}>AI Assistant</span>
        <button
          className="ml-auto p-2 rounded-full hover:bg-gray-200/60 text-white"
          onClick={() => {
            setExpanded(!expanded);
            if (window.updateActivity) window.updateActivity();
          }}
          aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {expanded ? <ChevronLeftIcon className="h-5 w-5 text-white" /> : <ChevronRightIcon className="h-5 w-5 text-white" />}
        </button>
      </div>
      <nav className="flex-1 mt-2">
        {navigation.map((item) => (
          <a
            key={item.name}
            href={item.href}
            className={classNames(
              'text-white/80 hover:bg-white/20 hover:text-white',
              'group flex items-center px-3 py-3 text-base font-semibold rounded-xl mt-4transition-all duration-200',
              !expanded && 'justify-center'
            )}
            onClick={item.name === 'New Chat' ? (e) => {
              e.preventDefault();
              setSelectedChatId(null);
              setSelectedChatMessages([]);
              if (window.updateActivity) window.updateActivity();
            } : undefined}
          >
            <item.icon
              className={classNames(
                item.current ? 'text-white' : 'text-white/70 group-hover:text-white',
                'h-6 w-6',
                expanded ? 'mr-4' : ''
              )}
              aria-hidden="true"
            />
            {expanded && <span className="tracking-wide">{item.name}</span>}
          </a>
        ))}
      </nav>
      {/* Space and horizontal line above chat history (hidden when sidebar is retracted) */}
      <div className={`w-full ${expanded ? 'px-4' : 'px-0'} mt-8 mb-8`} style={{ display: expanded ? 'block' : 'none' }}>
        <hr className="border-t border-white/20" />
      </div>
      {/* Chat History Section fills space above buttons */}
      <div className={`flex flex-col ${expanded ? 'px-2' : 'px-0'} mt-2 flex-1`}>
        {expanded && <div className="font-semibold text-xs uppercase text-white/60 mb-2 px-2">Chat History</div>}
        <div
          className={`flex-1 overflow-y-auto ${expanded ? 'rounded-xl' : ''} bg-black/10 border border-white/10 ${expanded ? 'px-2 py-2' : 'px-0 py-0'} space-y-1 flex flex-col sidebar-chat-history`}
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none', maxHeight: '28rem' }}
        >
          {/* Hide scrollbar for Chrome, Safari and Opera */}
          <style>{`
            .sidebar-chat-history::-webkit-scrollbar { display: none; }
          `}</style>
          {!user ? (
            expanded ? (
              <div className="flex-1 flex items-center justify-center text-white/40 text-xs py-8">Login to save the messages</div>
            ) : (
              <div className="flex-1" />
            )
          ) : (
            chatHistory.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-white/40 text-xs py-8">No chat history yet</div>
            ) : (
              chatHistory.map(chat => (
                <button
                  key={chat.session_id}
                  className={`w-full text-left px-2 py-2 rounded-lg hover:bg-gray-100/80 transition flex items-center gap-2 ${expanded ? '' : 'justify-center'} ${selectedChatId === chat.session_id ? 'bg-purple-100/30' : ''}`}
                  data-sessionid={chat.session_id}
                  onClick={async (e) => {
                    if (window.updateActivity) window.updateActivity();
                    const sessionId = e.currentTarget.getAttribute('data-sessionid');
                    setSelectedChatId(sessionId);
                    if (sessionId) {
                      try {
                        const res = await fetch(`http://localhost:3001/api/chats/${sessionId}`);
                        const data = await res.json();
                        if (data && data.messages) {
                          setSelectedChatMessages(data.messages);
                        }
                      } catch (err) {
                        console.error('Failed to fetch chat:', err);
                      }
                    } else {
                      setSelectedChatMessages([]);
                    }
                  }}
                >
                  {expanded
                    ? <span className="flex-1 whitespace-normal break-words">{chat.title}</span>
                    : <span className="flex items-center justify-center w-full"><InboxIcon className="h-5 w-5 text-gray-500" /></span>
                  }
                </button>
              ))
            )
          )}
        </div>
      </div>

      <div className={`absolute bottom-0 left-0 w-full flex flex-col gap-2 pb-4 ${expanded ? 'px-4' : 'px-0'}`}> 
  {/* ...existing code... */}
      </div>
    </div>
  )
}