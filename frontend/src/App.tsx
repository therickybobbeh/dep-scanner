import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import HomePage from './pages/HomePage';
import ScanPage from './pages/ScanPage';
import ReportPage from './pages/ReportPage';
import Header from './components/Header';

function App() {
  return (
    <Router>
      <div className="min-vh-100 bg-light">
        <Header />
        <main>
          <Container fluid>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/scan" element={<ScanPage />} />
              <Route path="/report/:jobId" element={<ReportPage />} />
            </Routes>
          </Container>
        </main>
      </div>
    </Router>
  );
}

export default App;
