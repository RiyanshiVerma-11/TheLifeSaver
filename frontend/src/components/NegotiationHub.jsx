import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Mail, Send, Copy, Trash2, Edit3, ArrowRight, CheckCircle } from 'lucide-react';

const NegotiationHub = () => {
  const { emailDrafts, updateEmailDraft, sendEmailDraft, deleteEmailDraft, tasks } = useApp();
  const [selectedDraftId, setSelectedDraftId] = useState(emailDrafts[0]?.id || null);
  const [editMode, setEditMode] = useState(false);
  const [editRecipient, setEditRecipient] = useState('');
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [copied, setCopied] = useState(false);

  const selectedDraft = emailDrafts.find(d => d.id === selectedDraftId) || emailDrafts[0];

  const handleSelectDraft = (draft) => {
    setSelectedDraftId(draft.id);
    setEditMode(false);
    setCopied(false);
  };

  const startEdit = () => {
    if (!selectedDraft) return;
    setEditRecipient(selectedDraft.recipient);
    setEditSubject(selectedDraft.subject);
    setEditBody(selectedDraft.body);
    setEditMode(true);
  };

  const saveEdit = async () => {
    if (!selectedDraft) return;
    await updateEmailDraft(selectedDraft.id, {
      recipient: editRecipient,
      subject: editSubject,
      body: editBody,
      status: selectedDraft.status
    });
    setEditMode(false);
  };

  const handleCopy = () => {
    if (!selectedDraft) return;
    navigator.clipboard.writeText(selectedDraft.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSend = async () => {
    if (!selectedDraft) return;
    await sendEmailDraft(selectedDraft.id);
    
    // Construct and open Gmail compose URL in a new tab
    const to = encodeURIComponent(selectedDraft.recipient);
    const subject = encodeURIComponent(selectedDraft.subject);
    const body = encodeURIComponent(selectedDraft.body);
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${subject}&body=${body}`;
    window.open(gmailUrl, '_blank');
  };

  const handleDelete = async () => {
    if (!selectedDraft) return;
    await deleteEmailDraft(selectedDraft.id);
    setSelectedDraftId(null);
  };

  return (
    <div className="negotiation-container">
      <header className="section-header">
        <div>
          <h2>Negotiation Hub</h2>
          <p className="subtitle">AI-drafted extension requests, apologies, and rescheduling messages.</p>
        </div>
      </header>

      {emailDrafts.length === 0 ? (
        <div className="empty-state glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <Mail size={48} className="text-muted" style={{ marginBottom: '1rem', opacity: 0.5 }} />
          <h3>Zero Backlog Conflicts</h3>
          <p className="subtitle">The AI Prediction Engine currently forecasts that you are tracking safely on all active deadlines. No negotiation templates required.</p>
        </div>
      ) : (
        <div className="negotiation-grid grid-split">
          {/* Drafts Sidebar */}
          <div className="drafts-sidebar glass-card">
            <div className="card-header">
              <Mail size={16} color="#00f0ff" />
              <h3>Generated Drafts ({emailDrafts.length})</h3>
            </div>
            
            <div className="draft-list">
              {emailDrafts.map(draft => {
                const associatedTask = tasks.find(t => t.id === draft.task_id);
                const isSelected = selectedDraft?.id === draft.id;
                return (
                  <div 
                    key={draft.id} 
                    onClick={() => handleSelectDraft(draft)}
                    className={`draft-item-card ${isSelected ? 'selected' : ''} ${draft.status === 'Sent' ? 'sent' : ''}`}
                  >
                    <div className="draft-item-header">
                      <span className={`status-badge ${draft.status === 'Sent' ? 'success' : 'pending'}`}>
                        {draft.status}
                      </span>
                      <span className="draft-date">{new Date(draft.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
                    </div>
                    <h5>{draft.subject}</h5>
                    <p className="draft-task-ref">Ref: {associatedTask ? associatedTask.title : 'Task Deadline'}</p>
                    <p className="draft-recipient-preview">To: {draft.recipient}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Draft Editor / Viewer Panel */}
          {selectedDraft ? (
            <div className="draft-viewer-panel glass-card">
              <div className="viewer-header">
                <div className="viewer-title-area">
                  <h3>{selectedDraft.subject}</h3>
                  <span className={`status-badge ${selectedDraft.status === 'Sent' ? 'success' : 'pending'}`}>
                    {selectedDraft.status}
                  </span>
                </div>
                
                {selectedDraft.status !== 'Sent' && (
                  <div className="viewer-actions-row">
                    {editMode ? (
                      <>
                        <button onClick={saveEdit} className="btn btn-accent btn-sm">Save Changes</button>
                        <button onClick={() => setEditMode(false)} className="btn btn-muted btn-sm">Cancel</button>
                      </>
                    ) : (
                      <>
                        <button onClick={startEdit} className="btn btn-muted btn-sm"><Edit3 size={12} /> Edit</button>
                        <button onClick={handleCopy} className="btn btn-muted btn-sm">
                          {copied ? <><CheckCircle size={12} className="text-green" /> Copied!</> : <><Copy size={12} /> Copy Text</>}
                        </button>
                        <button onClick={handleSend} className="btn btn-accent btn-sm"><Send size={12} /> Send via Gmail</button>
                        <button onClick={handleDelete} className="btn btn-danger btn-sm"><Trash2 size={12} /></button>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div className="email-meta-fields">
                <div className="meta-field">
                  <span className="field-label">To:</span>
                  {editMode ? (
                    <input 
                      type="text" 
                      value={editRecipient} 
                      onChange={e => setEditRecipient(e.target.value)} 
                      className="edit-meta-input"
                    />
                  ) : (
                    <span className="field-value">{selectedDraft.recipient}</span>
                  )}
                </div>
                <div className="meta-field">
                  <span className="field-label">Subject:</span>
                  {editMode ? (
                    <input 
                      type="text" 
                      value={editSubject} 
                      onChange={e => setEditSubject(e.target.value)} 
                      className="edit-meta-input"
                    />
                  ) : (
                    <span className="field-value font-weight-bold">{selectedDraft.subject}</span>
                  )}
                </div>
              </div>

              <div className="email-body-content">
                {editMode ? (
                  <textarea 
                    value={editBody} 
                    onChange={e => setEditBody(e.target.value)} 
                    className="edit-body-textarea"
                    rows={12}
                  />
                ) : (
                  <div className="rendered-email-body">
                    {selectedDraft.body.split('\n').map((line, idx) => (
                      <p key={idx}>{line}</p>
                    ))}
                  </div>
                )}
              </div>

              {selectedDraft.status === 'Sent' && (
                <div className="sent-overlay-info">
                  <CheckCircle size={20} color="#10b981" />
                  <p>This negotiation draft was pushed to Gmail. Check your sent messages folder for delivery updates.</p>
                </div>
              )}
            </div>
          ) : (
            <div className="draft-viewer-panel glass-card empty-viewer">
              <p>Select a draft from the left side panel to inspect or edit details.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NegotiationHub;
