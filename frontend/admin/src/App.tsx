import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import AdminLayout from './components/layout/AdminLayout';
import ToastContainer from './components/ui/Toast';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import KnowledgeBase from './pages/KnowledgeBase';
import Tools from './pages/Tools';
import AgentConfig from './pages/AgentConfig';
import Conversations from './pages/Conversations';
import Feedback from './pages/Feedback';

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="knowledge" element={<KnowledgeBase />} />
          <Route path="tools" element={<Tools />} />
          <Route path="agents" element={<AgentConfig />} />
          <Route path="conversations" element={<Conversations />} />
          <Route path="feedback" element={<Feedback />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
