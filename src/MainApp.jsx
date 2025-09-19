import Sidebar from './Sidebar';
import Navbar from './Navbar';
import MainContent from './MainContent';
import { useState, useEffect } from 'react';

export default function MainApp() {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedChatMessages, setSelectedChatMessages] = useState([]);
  const [user, setUser] = useState(null);

  // Load user from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('user');
    if (stored) {
      setUser(JSON.parse(stored));
    }
  }, []);

  // Logout handler
  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  return (
    <div className="min-h-screen bg-black flex flex-col md:flex-row">
      <div className="md:static md:flex-shrink-0 md:w-auto w-full z-30">
        <Sidebar
          expanded={sidebarExpanded}
          setExpanded={setSidebarExpanded}
          selectedChatId={selectedChatId}
          setSelectedChatId={setSelectedChatId}
          chatHistory={chatHistory}
          setChatHistory={setChatHistory}
          setSelectedChatMessages={setSelectedChatMessages}
          user={user}
          setUser={setUser}
        />
      </div>
      <div className="flex flex-col flex-1">
        <Navbar sidebarExpanded={sidebarExpanded} user={user} setUser={setUser} onLogout={handleLogout} />
        <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
          <MainContent
            messages={selectedChatMessages}
            sessionId={selectedChatId}
          />
        </main>
      </div>
    </div>
  );
}
