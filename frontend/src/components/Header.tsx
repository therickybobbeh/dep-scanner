import React from 'react';
import { Link } from 'react-router-dom';
import { Navbar, Nav, Container, Button } from 'react-bootstrap';
import { Shield } from 'lucide-react';

const Header: React.FC = () => {
  return (
    <Navbar bg="white" expand="lg" className="shadow-sm border-bottom">
      <Container>
        <Navbar.Brand as={Link as any} to="/" className="d-flex align-items-center">
          <Shield className="me-2" size={32} color="#4f46e5" />
          <span className="fw-bold fs-3 text-primary">DepScan</span>
        </Navbar.Brand>

        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        
        <Navbar.Collapse id="basic-navbar-nav" className="justify-content-end">
          <Nav className="align-items-center">
            <Nav.Link as={Link as any} to="/" className="me-3">
              Home
            </Nav.Link>
            <Button 
              as={Link as any} 
              to="/scan" 
              variant="primary" 
              size="sm"
            >
              New Scan
            </Button>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default Header;
