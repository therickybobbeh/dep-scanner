import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import HomePage from './pages/HomePage';
import ScanPage from './pages/ScanPage';
import ReportPage from './pages/ReportPage';
import Header from './components/Header';

// Layout component
function Layout() {
  return (
    <div className="min-vh-100">
      <Header />
      <main>
        <Container fluid>
          <Outlet />
        </Container>
      </main>
    </div>
  );
}

// Create the router with data router API
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "scan",
        element: <ScanPage />,
      },
      {
        path: "report/:jobId",
        element: <ReportPage />,
      },
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
