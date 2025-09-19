import { useNavigate } from 'react-router-dom';

export default function WelcomePage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-black via-gray-900 to-black/80">
      <div className="max-w-2xl w-full flex flex-col items-center justify-center bg-black/60 backdrop-blur-lg rounded-3xl shadow-2xl border border-white/10 p-12">
        <h1 className="text-5xl font-extrabold text-white mb-6 tracking-wide text-center drop-shadow-lg">Welcome to AI Assistant</h1>
        <p className="text-lg text-white/70 mb-10 text-center max-w-lg">Your all-in-one chat and productivity platform. Organize, chat, and get things done with a beautiful, modern interface.</p>
        <button
          className="bg-gradient-to-r from-purple-600 via-pink-500 to-red-500 text-white font-bold py-3 px-10 rounded-xl shadow-lg hover:scale-105 transition-all duration-150 text-xl"
          onClick={() => navigate('/login')}
        >
          Get Started
        </button>
      </div>
    </div>
  );
}
