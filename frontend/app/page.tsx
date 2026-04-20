"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchGallery,
  uploadSecret,
  extractSecret,
  getImageUrl,
  getDownloadUrl,
  deleteImage,
  login,
  setAuthToken,
  seedDecoyPhotos,
  uploadCarrier,
  ImageInfo,
} from "./api";

// ═══════════════════════════════════════════════
//  Toast Notifications
// ═══════════════════════════════════════════════
function ToastContainer({ toasts, onDismiss }: { toasts: { id: number; message: string; type: "success" | "error" }[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`} onClick={() => onDismiss(t.id)}>
          <span>{t.type === "success" ? "✓" : "✕"}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════
//  Dashboard / Landing Page
// ═══════════════════════════════════════════════
import { supabase } from "./supabaseClient";
import { setupVault, checkVaultStatus, setVaultToken } from "./api";
import type { Session } from "@supabase/supabase-js";

function DashboardScreen({ onLoginSuccess }: { onLoginSuccess: (mode: "real" | "panic") => void }) {
  const [session, setSession] = useState<Session | null>(null);
  const [hasPassword, setHasPassword] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        window.location.href = '/auth';
      } else {
        setSession(session);
        setAuthToken(session.access_token);
        // Check if vault password is set
        checkVaultStatus().then(res => {
           setHasPassword(res.has_password);
           setLoading(false);
        }).catch(() => {
           setError("Failed to verify vault status.");
           setLoading(false);
        });
      }
    });
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    window.location.href = '/auth';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setLoading(true); setError(""); 
    try {
      if (!hasPassword) {
        // Setup Vault
        const res = await setupVault(password);
        setVaultToken(res.access_token);
        onLoginSuccess(res.mode);
      } else {
        // Unlock Vault
        const res = await login(password);
        setVaultToken(res.access_token);
        onLoginSuccess((res as unknown as {mode: "real" | "panic"}).mode);
      }
    } catch {
      setError(hasPassword ? "Failed to unlock." : "Failed to setup password.");
    } finally {
      setLoading(false);
    }
  };

  if (!session || hasPassword === null) {
      return <div style={{height: "100vh", display: "flex", justifyContent: "center", alignItems: "center"}}><span className="spinner" style={{width: 50, height: 50, borderColor: "var(--accent)", borderTopColor: "transparent"}}></span></div>;
  }

  return (
    <div className="lock-screen-container" style={{ padding: "20px" }}>
      <div className="lock-bg-blob blob-1"></div>
      <div className="lock-bg-blob blob-2"></div>
      
      <div className="lock-card" style={{ maxWidth: "420px", padding: "40px", margin: "auto", position: "relative", zIndex: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" }}>
          <div>
              <h1 className="lock-title" style={{ margin: 0, fontSize: "28px" }}>☁ Cloud Vault</h1>
              <span style={{ fontSize: "13px", opacity: 0.6 }}>{session.user.email}</span>
          </div>
          <button className="btn btn-ghost" onClick={handleSignOut} style={{fontSize: "13px", padding: "8px 12px"}}>Sign Out</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <p className="lock-subtitle" style={{marginBottom: "20px"}}>
            {hasPassword ? "Enter your Secret Vault Password:" : "Setup a Password for your Secret Vault:"}
          </p>
          <div className="form-group">
            <input className="form-input" type="password" placeholder="Password..." value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: "100%", height: "54px", marginTop: "10px", fontSize: "16px" }} disabled={loading || !password}>
            {loading ? <span className="spinner"></span> : (hasPassword ? "Unlock Vault" : "Set Password & Enter")}
          </button>
        </form>

        {error && <div className="status-bar status-error" style={{ justifyContent: "center", marginTop: "20px" }}>✕ {error}</div>}
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════
//  Upload Modal (Steganography - Real Mode)
// ═══════════════════════════════════════════════
function UploadModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (msg: string) => void }) {
  const [secretFile, setSecretFile] = useState<File | null>(null);
  const [carrierFile, setCarrierFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [description, setDescription] = useState("nature landscape");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) setSecretFile(file);
  }, []);

  const handleSubmit = async () => {
    if (!secretFile || !password) {
      setError("Please select a file and enter a password.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await uploadSecret(secretFile, password, carrierFile || undefined, description);
      onSuccess(result.message);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">🔐 Hide a Secret File</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {/* Secret File Drop Zone */}
          <div
            className={`dropzone ${dragActive ? "active" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("secret-input")?.click()}
          >
            <div className="dropzone-icon">📄</div>
            <div className="dropzone-text">
              {secretFile ? "" : "Drop your secret file here, or click to browse"}
            </div>
            <div className="dropzone-hint">
              {secretFile ? "" : "Supports: .txt, .pdf, .json, .zip, .key, .pem, and more"}
            </div>
            {secretFile && (
              <div className="dropzone-filename">
                ✓ {secretFile.name} ({(secretFile.size / 1024).toFixed(1)} KB)
              </div>
            )}
            <input
              id="secret-input"
              type="file"
              style={{ display: "none" }}
              onChange={(e) => setSecretFile(e.target.files?.[0] || null)}
            />
          </div>

          {/* Password */}
          <div className="form-group">
            <label className="form-label">Encryption Password</label>
            <input
              className="form-input"
              type="password"
              placeholder="Enter a strong password..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <div className="form-hint">AES-256-GCM encryption. Remember this password — you{"'"}ll need it to extract the file.</div>
          </div>

          {/* Carrier Image (Optional) */}
          <div className="form-group">
            <label className="form-label">Carrier Image (optional)</label>
            <div style={{ display: "flex", gap: "10px" }}>
              <input
                className="form-input"
                type="text"
                placeholder="Image theme (e.g., sunset, mountains)..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                style={{ flex: 1 }}
              />
              <button
                className="btn btn-secondary"
                onClick={() => document.getElementById("carrier-input")?.click()}
                style={{ whiteSpace: "nowrap" }}
              >
                📷 Browse
              </button>
            </div>
            <div className="form-hint">
              {carrierFile
                ? `Using: ${carrierFile.name}`
                : "A real photo will be generated by AI if none is provided."}
            </div>
            <input
              id="carrier-input"
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => setCarrierFile(e.target.files?.[0] || null)}
            />
          </div>

          {/* Submit */}
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || !secretFile || !password}
            style={{ width: "100%" }}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Encrypting & Hiding...
              </>
            ) : (
              <>🔒 Encrypt & Hide File</>
            )}
          </button>

          {error && <div className="status-bar status-error">✕ {error}</div>}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
//  Normal Upload Modal (Panic Mode / Carrier)
// ═══════════════════════════════════════════════
function NormalUploadModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (msg: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const uploadedFile = e.dataTransfer.files[0];
    if (uploadedFile && uploadedFile.type.startsWith("image/")) setFile(uploadedFile);
  }, []);

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      await uploadCarrier(file);
      onSuccess("Photo uploaded successfully.");
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">📷 Upload Photo</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div
            className={`dropzone ${dragActive ? "active" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("photo-input")?.click()}
          >
            <div className="dropzone-icon">🖼️</div>
            <div className="dropzone-text">
              {file ? "" : "Drop your photo here, or click to browse"}
            </div>
            {file && (
              <div className="dropzone-filename">
                ✓ {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </div>
            )}
            <input
              id="photo-input"
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || !file}
            style={{ width: "100%" }}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Uploading...
              </>
            ) : (
              <>Upload</>
            )}
          </button>

          {error && <div className="status-bar status-error">✕ {error}</div>}
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════
//  Extract Modal
// ═══════════════════════════════════════════════
function ExtractModal({ image, onClose, onSuccess }: { image: ImageInfo; onClose: () => void; onSuccess: (msg: string) => void }) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [extractedName, setExtractedName] = useState("");
  const [extractedSize, setExtractedSize] = useState("");

  const handleExtract = async () => {
    if (!password) { setError("Enter password."); return; }
    setLoading(true);
    setError("");
    setDownloadUrl(null);
    try {
      const result = await extractSecret(image.id, password);
      setDownloadUrl(getDownloadUrl(result.download_url));
      setExtractedName(result.extracted_file);
      setExtractedSize(result.file_size);
      onSuccess(`Extracted "${result.extracted_file}" successfully!`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Extraction failed — wrong password?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">🔓 Extract Hidden File</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={getImageUrl(image.id)}
            alt={image.original_name}
            className="detail-image"
          />


          <div className="detail-row">
            <span className="detail-label">Resolution</span>
            <span className="detail-value">{image.resolution}</span>
          </div>

          <div className="form-group" style={{ marginTop: 24 }}>
            <label className="form-label">Decryption Password</label>
            <input
              className="form-input"
              type="password"
              placeholder="Enter the master password..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleExtract()}
            />
          </div>

          {!downloadUrl ? (
            <button
              className="btn btn-primary"
              onClick={handleExtract}
              disabled={loading || !password}
              style={{ width: "100%" }}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Decrypting...
                </>
              ) : (
                <>🔓 Decrypt & Extract</>
              )}
            </button>
          ) : (
            <div style={{ textAlign: "center" }}>
              <div className="status-bar status-success" style={{ marginTop: 0, marginBottom: 16 }}>
                ✓ Extracted: {extractedName} ({extractedSize})
              </div>
              <a
                href={downloadUrl}
                download={extractedName}
                className="btn btn-primary"
                style={{ width: "100%", textDecoration: "none" }}
              >
                ⬇ Download {extractedName}
              </a>
            </div>
          )}

          {error && <div className="status-bar status-error">✕ {error}</div>}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
//  Image Detail Modal
// ═══════════════════════════════════════════════
function DetailModal({ image, mode, onClose, onExtract, onDelete }: {
  image: ImageInfo;
  mode: "real" | "panic";
  onClose: () => void;
  onExtract: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">📷 Photo Details</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={getImageUrl(image.id)}
            alt={image.original_name}
            className="detail-image"
          />

          {/* Status explicitly removed to maintain subtly */}
          
          <div className="detail-row">
            <span className="detail-label">Resolution</span>
            <span className="detail-value">{image.resolution}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">File Size</span>
            <span className="detail-value">{image.file_size}</span>
          </div>
          

          <div className="detail-actions">
            {mode === "real" && image.has_hidden_data && (
              <button className="btn btn-primary" onClick={onExtract} style={{ flex: 1 }}>
                🔓 Extract File
              </button>
            )}
            <button className="btn btn-danger" onClick={onDelete} style={{ flex: mode === "panic" || !image.has_hidden_data ? 1 : 0 }}>
              🗑 Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
//  Main Gallery Page
// ═══════════════════════════════════════════════
export default function GalleryPage() {
  const [authMode, setAuthMode] = useState<"none" | "real" | "panic">("none");
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modals state
  const [showStegoUpload, setShowStegoUpload] = useState(false);
  const [showNormalUpload, setShowNormalUpload] = useState(false);
  
  const [selectedImage, setSelectedImage] = useState<ImageInfo | null>(null);
  const [extractImage, setExtractImage] = useState<ImageInfo | null>(null);
  const [filter, setFilter] = useState<string | undefined>();
  const [toasts, setToasts] = useState<{ id: number; message: string; type: "success" | "error" }[]>([]);

  const addToast = (message: string, type: "success" | "error") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  };

  const loadGallery = useCallback(async () => {
    if (authMode === "none") return;
    setLoading(true);
    try {
      // In panic mode, force filter to undefined or let backend handle it
      const data = await fetchGallery(authMode === "panic" ? undefined : filter);
      setImages(data.images);
    } catch {
      addToast("Failed to load gallery", "error");
    } finally {
      setLoading(false);
    }
  }, [filter, authMode]);

  useEffect(() => {
    if (authMode !== "none") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadGallery();
    }
  }, [loadGallery, authMode]);

  const handleDelete = async (imageId: string) => {
    try {
      await deleteImage(imageId);
      addToast("Image deleted", "success");
      setSelectedImage(null);
      loadGallery();
    } catch {
      addToast("Failed to delete image", "error");
    }
  };

  const handleSeedDecoy = async () => {
    try {
      addToast("Seeding decoy gallery...", "success");
      await seedDecoyPhotos();
      loadGallery();
      addToast("Decoy photos added", "success");
    } catch {
      addToast("Failed to seed decoy photos", "error");
    }
  }

  const handleLogout = () => {
    setAuthToken(null);
    setAuthMode("none");
    setImages([]);
    setFilter(undefined);
  }

  if (authMode === "none") {
    return <DashboardScreen onLoginSuccess={setAuthMode} />;
  }

  return (
    <>
      <ToastContainer toasts={toasts} onDismiss={(id) => setToasts((p) => p.filter((t) => t.id !== id))} />

      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <div className="navbar-logo">☁</div>
          <div>
            <div className="navbar-title">Cloud Vault</div>
            <div className="navbar-subtitle">Personal Photos</div>
          </div>
        </div>
        <div className="navbar-actions">
          {authMode === "real" && (
            <>
              <button className="btn btn-ghost" onClick={handleSeedDecoy}>
                🌱 Seed Decoy
              </button>
              <select
                className="form-input"
                value={filter || ""}
                onChange={(e) => setFilter(e.target.value || undefined)}
                style={{ width: "auto", padding: "10px 16px" }}
              >
                <option value="">All Photos</option>
                <option value="hidden">🔐 With Secrets</option>
                <option value="clean">📷 Clean Only</option>
              </select>
            </>
          )}

          {authMode === "real" ? (
            <button className="btn btn-primary" onClick={() => setShowStegoUpload(true)}>
              + Hide a File
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => setShowNormalUpload(true)}>
              + Upload Photo
            </button>
          )}
          
          <button className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {/* Gallery */}
      <div className="gallery-container">
        <div className="gallery-header">
          <h1 className="gallery-title">
            Gallery
            <span className="gallery-count">{images.length} photos</span>
          </h1>
        </div>

        {loading ? (
          <div className="empty-state">
            <div className="spinner" style={{ width: 40, height: 40, margin: "0 auto", borderColor: "var(--accent)", borderTopColor: "transparent" }}></div>
          </div>
        ) : images.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🖼️</div>
            <div className="empty-title">No photos yet</div>
            <div className="empty-text">
              Securely store your personal photos and memories in the cloud.
            </div>
            {authMode === "real" ? (
              <button className="btn btn-primary" onClick={() => setShowStegoUpload(true)}>
                + Hide Your First File
              </button>
            ) : (
              <button className="btn btn-primary" onClick={() => setShowNormalUpload(true)}>
                + Upload Photo
              </button>
            )}
          </div>
        ) : (
          <div className="gallery-grid">
            {images.map((img) => (
              <div
                key={img.id}
                className="image-card"
                onClick={() => setSelectedImage(img)}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getImageUrl(img.id)}
                  alt={img.original_name}
                  className="image-card-img"
                  loading="lazy"
                />
                <div className="image-card-overlay">
                  <div className="image-card-name">{img.original_name}</div>
                  <div className="image-card-meta">
                    <span>{img.resolution}</span>
                    <span>•</span>
                    <span>{img.file_size}</span>
                    
                    {authMode === "real" && img.has_hidden_data && (
                      <span style={{ marginLeft: "auto", fontSize: "12px", opacity: 0.7 }}>🔒</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {showStegoUpload && (
        <UploadModal
          onClose={() => setShowStegoUpload(false)}
          onSuccess={(msg) => { addToast(msg, "success"); loadGallery(); }}
        />
      )}

      {showNormalUpload && (
        <NormalUploadModal
          onClose={() => setShowNormalUpload(false)}
          onSuccess={(msg) => { addToast(msg, "success"); loadGallery(); }}
        />
      )}

      {selectedImage && !extractImage && (
        <DetailModal
          mode={authMode}
          image={selectedImage}
          onClose={() => setSelectedImage(null)}
          onExtract={() => {
            setExtractImage(selectedImage);
            setSelectedImage(null);
          }}
          onDelete={() => handleDelete(selectedImage.id)}
        />
      )}

      {extractImage && (
        <ExtractModal
          image={extractImage}
          onClose={() => setExtractImage(null)}
          onSuccess={(msg) => addToast(msg, "success")}
        />
      )}
    </>
  );
}
