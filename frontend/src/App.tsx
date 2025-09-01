import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import HomePage from './pages/HomePage';
import ScanPage from './pages/ScanPage';
import ReportPage from './pages/ReportPage';
import Header from './components/Header';

function App() {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <div className="min-vh-100">
        <Header />
        <main>
          <Container fluid>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/new-scan" element={<ScanPage />} />
              <Route path="/results/:jobId" element={<ReportPage />} />
            </Routes>
          </Container>
        </main>
      </div>
    </Router>
  );
}

export default App;
