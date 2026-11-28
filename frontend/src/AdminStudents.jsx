
import { useEffect, useState } from "react";
import axios from "axios";
import {
  Users,
  Search,
  RefreshCw,
  Mail,
  User
} from "lucide-react";
import "./AdminStudents.css";

const API = "http://localhost:5000/api/admin/students/";

function AdminStudents() {
  const [students, setStudents] = useState([]);
  const [totalStudents, setTotalStudents] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStudents = async () => {
    try {
      setError("");

      const response = await axios.get(API, {
        withCredentials: true
      });

      setStudents(response.data.students || []);
      setTotalStudents(response.data.total_students || 0);
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to load student details."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const filteredStudents = students.filter((student) => {
    const name = student.full_name?.toLowerCase() || "";
    const email = student.email?.toLowerCase() || "";
    const query = search.toLowerCase();

    return name.includes(query) || email.includes(query);
  });

  return (
    <div className="admin-students-page">

      <div className="admin-students-header">
        <div>
          <h2>Student Management</h2>
          <p>View and manage registered student accounts.</p>
        </div>

        <button
          className="students-refresh-button"
          onClick={() => {
            setLoading(true);
            fetchStudents();
          }}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="students-summary-card">
        <div className="students-summary-icon">
          <Users size={26} />
        </div>

        <div>
          <h3>{totalStudents}</h3>
          <p>Total Registered Students</p>
        </div>
      </div>

      <div className="students-table-section">

        <div className="students-section-header">
          <div>
            <h3>Registered Students</h3>
            <p>Student account information</p>
          </div>

          <div className="students-search">
            <Search size={17} />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="students-message">
            Loading students...
          </div>
        ) : error ? (
          <div className="students-error">
            {error}
            <button onClick={fetchStudents}>
              Try Again
            </button>
          </div>
        ) : filteredStudents.length === 0 ? (
          <div className="students-message">
            {search
              ? "No students match your search."
              : "No registered students found."}
          </div>
        ) : (
          <div className="students-table-wrapper">
            <table className="students-table">
              <thead>
                <tr>
                  <th>Student ID</th>
                  <th>Student Name</th>
                  <th>Email Address</th>
                </tr>
              </thead>

              <tbody>
                {filteredStudents.map((student) => (
                  <tr key={student.student_id}>
                    <td>#{student.student_id}</td>

                    <td>
                      <div className="student-name-cell">
                        <div className="student-avatar">
                          <User size={17} />
                        </div>
                        {student.full_name}
                      </div>
                    </td>

                    <td>
                      <div className="student-email-cell">
                        <Mail size={15} />
                        {student.email}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </div>
  );
}

export default AdminStudents;
