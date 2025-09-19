import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import WelcomePage from './WelcomePage';
import AuthPage from './AuthPage';
import MainApp from './MainApp';
import CalendarPage from './CalendarPage';

export default function RootApp() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/app" element={<MainApp />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}
