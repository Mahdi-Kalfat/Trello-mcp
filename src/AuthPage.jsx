import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AuthPage() {
  const [showRegister, setShowRegister] = useState(false);
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  // Handle login
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await fetch('http://localhost:3001/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
      });
      if (res.ok) {
        const data = await res.json();
        setSuccess('Login successful!');
        // Save user credentials to localStorage
        if (data && data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
        setTimeout(() => {
          navigate('/app');
        }, 500);
      } else {
        const data = await res.json();
        setError(data.message || 'Login failed');
      }
    } catch (err) {
      setError('Login failed');
    }
  };

  // Handle register
  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await fetch('http://localhost:3001/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registerData)
      });
      if (res.ok) {
        setSuccess('Account created! You can now log in.');
        setShowRegister(false);
      } else {
        const data = await res.json();
        setError(data.message || 'Registration failed');
      }
    } catch (err) {
      setError('Registration failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-black via-gray-900 to-black/80">
  <div className="relative w-full max-w-5xl flex shadow-2xl rounded-3xl overflow-hidden border border-white/10 bg-black/60 backdrop-blur-lg" style={{ minHeight: '700px', height: '80vh' }}>
        {/* Left Section: Login */}
        <div className="w-1/2 p-10 flex flex-col justify-center items-center transition-all duration-700" style={{ zIndex: 2 }}>
          <h2 className="text-3xl font-bold text-white mb-6 tracking-wide">Sign In</h2>
          <form className="w-full flex flex-col gap-4" onSubmit={handleLogin}>
            <input type="email" required placeholder="Email" className="rounded-lg px-4 py-2 bg-gray-900/80 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-purple-500" value={loginData.email} onChange={e => setLoginData({ ...loginData, email: e.target.value })} />
            <input type="password" required placeholder="Password" className="rounded-lg px-4 py-2 bg-gray-900/80 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-purple-500" value={loginData.password} onChange={e => setLoginData({ ...loginData, password: e.target.value })} />
            <button type="submit" className="bg-gradient-to-r from-purple-600 via-pink-500 to-red-500 text-white font-bold py-2 rounded-xl shadow-lg hover:scale-105 transition-all duration-150">Connect</button>
          </form>
        </div>
        {/* Right Section: Register */}
        <div className="w-1/2 p-10 flex flex-col justify-center items-center transition-all duration-700" style={{ zIndex: 2 }}>
          <h2 className="text-3xl font-bold text-white mb-6 tracking-wide">Register</h2>
          <form className="w-full flex flex-col gap-4" onSubmit={handleRegister}>
            <input type="text" required placeholder="Name" className="rounded-lg px-4 py-2 bg-gray-900/80 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-purple-500" value={registerData.name} onChange={e => setRegisterData({ ...registerData, name: e.target.value })} />
            <input type="email" required placeholder="Email" className="rounded-lg px-4 py-2 bg-gray-900/80 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-purple-500" value={registerData.email} onChange={e => setRegisterData({ ...registerData, email: e.target.value })} />
            <input type="password" required placeholder="Password" className="rounded-lg px-4 py-2 bg-gray-900/80 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-purple-500" value={registerData.password} onChange={e => setRegisterData({ ...registerData, password: e.target.value })} />
            <button type="submit" className="bg-gradient-to-r from-purple-600 via-pink-500 to-red-500 text-white font-bold py-2 rounded-xl shadow-lg hover:scale-105 transition-all duration-150">Create Account</button>
          </form>
        </div>
        {/* Sliding Card Overlay */}
  <div className={`absolute top-0 left-0 w-1/2 h-full bg-gradient-to-b from-black via-gray-900 to-black flex flex-col items-center justify-center transition-all duration-700 rounded-3xl shadow-2xl ${showRegister ? 'translate-x-full' : 'translate-x-0'}`} style={{ zIndex: 3, height: '100%', opacity: 1 }}>
          <div className="flex flex-col items-center px-8">
            <h3 className="text-2xl font-bold text-white mb-2">{showRegister ? 'Register' : 'Connect'}</h3>
            <p className="text-white/70 mb-6 text-center max-w-xs">{showRegister ? 'Create your account to get started!' : 'Welcome back! Please sign in to continue.'}</p>
            <button
              className="bg-gradient-to-r from-purple-600 via-pink-500 to-red-500 text-white font-bold py-2 px-8 rounded-xl shadow-lg hover:scale-105 transition-all duration-150"
              onClick={() => setShowRegister(!showRegister)}
            >
              {showRegister ? 'Connect' : 'Register'}
            </button>
          </div>
        </div>
        {/* Error/Success Message */}
        {(error || success) && (
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-50 bg-black/80 text-white px-6 py-3 rounded-xl shadow-lg border border-red-500/40">
            {error && <span className="text-red-400">{error}</span>}
            {success && <span className="text-green-400">{success}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
