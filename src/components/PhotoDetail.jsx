// src/components/PhotoDetail.jsx
import React, { useState, useEffect, useMemo } from "react";
import {
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  Edit,
  Search,
  Save,
  X,
  AlertTriangle,
  Info,
  Download,
} from "lucide-react";
import { ArtworkSearch } from "./ArtworkSearch";

export const PhotoDetail = ({ photo, onBack, onValidate }) => {
  const [newFilename, setNewFilename] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [customReason, setCustomReason] = useState("");
  const [photoDetails, setPhotoDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [existingArtwork, setExistingArtwork] = useState(null);
  const [showRenameForm, setShowRenameForm] = useState(false);
  const [showArtworkSearch, setShowArtworkSearch] = useState(false);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [showClassificationForm, setShowClassificationForm] = useState(false);
  const [classification, setClassification] = useState("");
  const [filledSlots, setFilledSlots] = useState([]);
  const [artworkCategory, setArtworkCategory] = useState("");
  const [validationLoading, setValidationLoading] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [filemakerData, setFilemakerData] = useState(null);
  const [filemakerLoading, setFilemakerLoading] = useState(false);
  const [certificateDownloading, setCertificateDownloading] = useState(false);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [scheduledDate, setScheduledDate] = useState("");
  const [artworkId, setArtworkId] = useState("");
  const [duplicateResolving, setDuplicateResolving] = useState(false);
  const [generatePerspective, setGeneratePerspective] = useState(false);
  const [selectedBackground, setSelectedBackground] = useState("");
  const [duplicateData, setDuplicateData] = useState(null);
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [validationDisabled, setValidationDisabled] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [imageLoading, setImageLoading] = useState(true);
  const [replacing, setReplacing] = useState(false);

  // Get user role from token
  const getUserRole = () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return null;

      // Decode JWT token (simple base64 decode for payload)
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.role;
    } catch (error) {
      console.error("Error decoding token:", error);
      return null;
    }
  };

  // Check if user can validate photos (admin or validator)
  const canValidatePhotos = () => {
    return userRole === "admin" || userRole === "validator";
  };

  // Fetch FileMaker data for the artwork
  const fetchFilemakerData = async (idName) => {
    if (!idName) return;

    setFilemakerLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/filemaker/artwork/${idName}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        setFilemakerData(data);
      } else {
        console.error("Failed to fetch FileMaker data");
      }
    } catch (error) {
      console.error("Error fetching FileMaker data:", error);
    } finally {
      setFilemakerLoading(false);
    }
  };

  // Resolve the artwork id for the current photo (used for slot status dots)
  const resolveArtworkId = () => {
    return (
      existingArtwork?.IdName ||
      photo?.artwork_id ||
      photo?.id?.match(/([A-Z]+-\d+)/)?.[1] ||
      photo?.filename?.match(/([A-Z]+-\d+)/)?.[1] ||
      null
    );
  };

  // Fetch which classification slots already contain an image (from the
  // photo_validator DB) so the classification dropdown can show 🟢 / 🔴.
  const fetchFilledSlots = async (idName) => {
    if (!idName) {
      setFilledSlots([]);
      return;
    }
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `/api/photos/artwork-slots/${encodeURIComponent(idName)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const data = await response.json();
        setFilledSlots(Array.isArray(data.filled) ? data.filled : []);
        setArtworkCategory(data.category || "");
      } else {
        setFilledSlots([]);
        setArtworkCategory("");
      }
    } catch (error) {
      console.warn("Error fetching filled slots:", error);
      setFilledSlots([]);
    }
  };

  // Refresh slot status whenever the target artwork changes
  useEffect(() => {
    fetchFilledSlots(resolveArtworkId());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photo, existingArtwork]);

  const rejectReasons = [
    "Poor quality photo",
    "Bad lighting",
    "Blurry photo",
    "Bad framing",
    "Reflections on artwork",
    "Artwork partially visible",
    "Color problem",
    "Inappropriate format",
    "Incorrect filename",
    "Artwork not found in database",
    "Other (specify)",
  ];

  // Image categories (client 2026 spec). Each is offered in LR and HR.
  // Sculptures also get "3/4 View". "Others" allows a free-text note.
  // A6 is a single format (no HR/LR).
  // Image classifications — MUST stay EXACTLY aligned with the Review2 tool.
  // (client spec: only these; Frame/Back/Perspective/Signature/Detail are single.)
  const IMAGE_CLASSIFICATIONS = [
    { value: "MAIN_HR",    label: "Main HR" },
    { value: "MAIN_LR",    label: "Main LR" },
    { value: "FRONT",      label: "Front" },
    { value: "FRONTRIGHT", label: "Frontright" },
    { value: "LEFT",       label: "Left" },
    { value: "BACK",       label: "Back" },
    { value: "BACKFRAME",  label: "Back Frame" },
    { value: "FRAME",      label: "Frame" },
    { value: "SIGN",       label: "Signature" },
    { value: "DET1",       label: "Det1" },
    { value: "DET2",       label: "Det2" },
    { value: "SCALE",      label: "Scale" },
    { value: "INSITU",     label: "In situ" },
    { value: "OTHERS",     label: "Others" },
  ];
  // Sculptures get one extra classification
  const SCULPTURE_CLASSIFICATIONS = [{ value: "VIEW34", label: "3/4 View" }];

  const classifications = [
    // Image classifications are generated dynamically (LR/HR per category
    // + A6 + sculpture-only views) in getAvailableClassifications below.

    // Classifications pour PDFs (certificats et documents) - 2 champs par catégorie
    {
      value: "CERT_AUTHENTICITY_1",
      label: "CERT_AUTHENTICITY_1 - Certificate of Authenticity #1",
      type: "pdf",
    },
    {
      value: "CERT_AUTHENTICITY_2",
      label: "CERT_AUTHENTICITY_2 - Certificate of Authenticity #2",
      type: "pdf",
    },
    {
      value: "CATALOG_RAISONNE_1",
      label: "CATALOG_RAISONNE_1 - Catalogue Raisonné #1",
      type: "pdf",
    },
    {
      value: "CATALOG_RAISONNE_2",
      label: "CATALOG_RAISONNE_2 - Catalogue Raisonné #2",
      type: "pdf",
    },
    {
      value: "EXHIBITION_CATALOG_1",
      label: "EXHIBITION_CATALOG_1 - Exhibition Catalogue / Publication #1",
      type: "pdf",
    },
    {
      value: "EXHIBITION_CATALOG_2",
      label: "EXHIBITION_CATALOG_2 - Exhibition Catalogue / Publication #2",
      type: "pdf",
    },
    {
      value: "CONDITION_REPORT_1",
      label: "CONDITION_REPORT_1 - Condition Report #1",
      type: "pdf",
    },
    {
      value: "CONDITION_REPORT_2",
      label: "CONDITION_REPORT_2 - Condition Report #2",
      type: "pdf",
    },
    { value: "OTHER_1", label: "OTHER_1 - Other Document #1", type: "pdf" },
    { value: "OTHER_2", label: "OTHER_2 - Other Document #2", type: "pdf" },

    // Classifications pour vidéos
    // {
    //   value: "VIDEO_PRESENTATION",
    //   label: "VIDEO_PRESENTATION - Artwork Presentation",
    //   type: "video",
    // },
    // {
    //   value: "VIDEO_DETAIL",
    //   label: "VIDEO_DETAIL - Detail Video",
    //   type: "video",
    // },
    // {
    //   value: "VIDEO_INSTALLATION",
    //   label: "VIDEO_INSTALLATION - Installation Process",
    //   type: "video",
    // },
    // {
    //   value: "VIDEO_TIMELAPSE",
    //   label: "VIDEO_TIMELAPSE - Creation Timelapse",
    //   type: "video",
    // },
    // {
    //   value: "VIDEO_DOCUMENTARY",
    //   label: "VIDEO_DOCUMENTARY - Documentary About Artwork",
    //   type: "video",
    // },
    // {
    //   value: "VIDEO_ARTIST_INTERVIEW",
    //   label: "VIDEO_ARTIST_INTERVIEW - Artist Interview",
    //   type: "video",
    // },
    {
      value: "VIDEO_PRESENTATION_1",
      label: "VIDEO_PRESENTATION #1",
      type: "video",
    },
    {
      value: "VIDEO_PRESENTATION_2",
      label: "VIDEO_PRESENTATION #2",
      type: "video",
    },

    {
      value: "VIDEO_DETAIL_1",
      label: "VIDEO_DETAIL #1",
      type: "video",
    },
    {
      value: "VIDEO_DETAIL_2",
      label: "VIDEO_DETAIL #2",
      type: "video",
    },

    {
      value: "VIDEO_INSTALLATION_1",
      label: "VIDEO_INSTALLATION #1",
      type: "video",
    },
    {
      value: "VIDEO_INSTALLATION_2",
      label: "VIDEO_INSTALLATION #2",
      type: "video",
    },

    {
      value: "VIDEO_TIMELAPSE_1",
      label: "VIDEO_TIMELAPSE #1",
      type: "video",
    },
    {
      value: "VIDEO_TIMELAPSE_2",
      label: "VIDEO_TIMELAPSE #2",
      type: "video",
    },

    {
      value: "VIDEO_DOCUMENTARY_1",
      label: "VIDEO_DOCUMENTARY #1",
      type: "video",
    },
    {
      value: "VIDEO_DOCUMENTARY_2",
      label: "VIDEO_DOCUMENTARY #2",
      type: "video",
    },

    {
      value: "VIDEO_INTERVIEW_1",
      label: "VIDEO_INTERVIEW #1",
      type: "video",
    },
    {
      value: "VIDEO_INTERVIEW_2",
      label: "VIDEO_INTERVIEW #2",
      type: "video",
    },

    // Classification universelle
    { value: "OTHER", label: "OTHER - Other (specify in notes)", type: "all" },
  ];

  // Get file type from photo object or filename
  const getFileType = () => {
    console.log("[DEBUG] getFileType called");
    console.log("[DEBUG] photoDetails:", photoDetails);
    console.log("[DEBUG] photo:", photo);

    // First try from photoDetails API response
    if (photoDetails?.file_type) {
      console.log(
        "[DEBUG] Using photoDetails.file_type:",
        photoDetails.file_type
      );
      return photoDetails.file_type;
    }

    // Then try from photo prop (from list API)
    if (photo?.file_type) {
      console.log("[DEBUG] Using photo.file_type:", photo.file_type);
      return photo.file_type;
    }

    // Fallback: detect from filename extension
    if (photo?.filename) {
      const ext = photo.filename.toLowerCase().split(".").pop();
      console.log(
        "[DEBUG] Detecting from filename:",
        photo.filename,
        "ext:",
        ext
      );
      if (["jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif"].includes(ext)) {
        console.log("[DEBUG] Detected as image");
        return "image";
      } else if (ext === "pdf") {
        console.log("[DEBUG] Detected as pdf");
        return "pdf";
      } else if (
        ["mp4", "avi", "mov", "wmv", "flv", "webm", "mkv"].includes(ext)
      ) {
        console.log("[DEBUG] Detected as video");
        return "video";
      }
    }
    console.log("[DEBUG] Falling back to image");
    return "image"; // Default fallback
  };

  // Get filtered classifications based on file type (recalculated when photoDetails changes)
  const getAvailableClassifications = useMemo(() => {
    const fileType = getFileType();
    if (fileType === "image") {
      // Review2-aligned; sculptures get "3/4 View" (added before "Others").
      const isSculpture = (artworkCategory || "").toLowerCase().includes("sculpt");
      let list = IMAGE_CLASSIFICATIONS;
      if (isSculpture) {
        const base = IMAGE_CLASSIFICATIONS.slice(0, -1);
        const others = IMAGE_CLASSIFICATIONS[IMAGE_CLASSIFICATIONS.length - 1];
        list = [...base, ...SCULPTURE_CLASSIFICATIONS, others];
      }
      return list.map((c) => ({ ...c, type: "image" }));
    }
    return classifications.filter(
      (cls) => cls.type === fileType || cls.type === "all"
    );
  }, [photo, photoDetails, artworkCategory]);

  // Initialize states
  useEffect(() => {
    if (photo) {
      setNewFilename(photo.filename || photo.id);
      fetchPhotoDetails();
    }

    // Initialize user role
    const role = getUserRole();
    setUserRole(role);
  }, [photo]);

  // Fetch photo details
  const fetchPhotoDetails = async () => {
    try {
      setLoading(true);

      const response = await fetch(
        `/api/photos/details/${encodeURIComponent(photo.id)}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      if (response.ok) {
        const details = await response.json();
        setPhotoDetails(details);
      }
    } catch (err) {
      console.warn("Error fetching photo details:", err);
    } finally {
      setLoading(false);
    }
  };

  // Download certificate function
  const downloadCertificate = async (artworkId) => {
    if (!artworkId) return;

    setCertificateDownloading(true);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/certificate/download/${artworkId}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        // Créer un lien de téléchargement
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Certificat_${artworkId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const error = await response.json();
        alert(`Error téléchargement: ${error.error || "Error inconnue"}`);
      }
    } catch (error) {
      console.error("Error téléchargement certificat:", error);
      alert("Error de connexion lors du téléchargement");
    } finally {
      setCertificateDownloading(false);
    }
  };

  // Handle scheduled validation
  const handleScheduledValidation = async () => {
    if (!scheduledDate || !classification) {
      alert("Please select a classification and a date");
      return;
    }

    try {
      setValidationLoading(true);
      setError(null);

      const payload = {
        photoId: photo.id,
        decision: "scheduled",
        classification: classification,
        scheduledDate: scheduledDate,
        newFilename: newFilename !== photo.filename ? newFilename : null,
        // Prespective  NEW FIELDS
        generatePerspective: generatePerspective,
        backgroundName: selectedBackground,
      };

      const token = localStorage.getItem("token");
      const response = await fetch("/api/photos/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        onValidate({
          ...photo,
          status: "scheduled",
          classification: classification,
          scheduledDate: scheduledDate,
        });
        alert("✅ Photo successfully scheduled for publication.");
        window.location.reload(); // 🔁 Refreshes the page completely

        setShowScheduleForm(false);
        setScheduledDate("");
      } else {
        setError(result.error || "Error lors de la programmation");
      }
    } catch (err) {
      setError("Error de connexion");
      setValidationDisabled(true); //
    } finally {
      setValidationLoading(false);
	
if (window.setAppView) {
        window.setAppView("validated");
      }
    }
  };

  // Handle artwork found
  const handleArtworkFound = (artwork) => {
    setExistingArtwork(artwork);
    // Fetch FileMaker data when artwork is found
    if (artwork && artwork.IdName) {
      fetchFilemakerData(artwork.IdName);
    }
  };

  // Handle rename
    const handleRenameSubmit = async (e) => {
  e.preventDefault();

  // ❌ No rename if input is empty
  if (!newFilename) {
    setShowRenameForm(false);
    return;
  }

  // ✅ ADDED:
  // Remove extension if user typed (.jpg, .png, .jpeg, .tiff, etc.)
  // Backend will preserve the ORIGINAL extension
  const cleanFilename = newFilename.replace(/\.[^/.]+$/, "");

  // ✅ ADDED:
  // Compare only base filename (ignore extension)
  const currentBaseName = photo.filename.replace(/\.[^/.]+$/, "");
  if (cleanFilename === currentBaseName) {
    setShowRenameForm(false);
    return;
  }

  try {
    setLoading(true);

    const response = await fetch("/api/photos/rename", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify({
        photoId: photo.id,

        // ✅ ADDED:
        // Send filename WITHOUT extension
        newFilename: cleanFilename,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Error during renaming");
    }

    const result = await response.json();
    setShowRenameForm(false);
    setError(null);

    // ✅ ADDED:
    // Update filename from backend response (with preserved extension)
    photo.filename = result.new_filename;

    if (result.new_photo_id) {
      photo.id = result.new_photo_id;
    }

    // Force refresh of the parent to update the photo list
    if (onBack) {
      // Slight delay to avoid race condition with backend/db
      setTimeout(() => {
        onBack();
      }, 500);
    }

  } catch (err) {
    setError(`Renaming error: ${err.message}`);
  } finally {
    setLoading(false);
  }
};


  // Handle validation
      const handleValidation = async (decision, reason = null) => {
    // Validate classification is required for validation
    if (decision && !classification) {
      alert("Please select a classification before validating");
      return;
    }
    if (getFileType() !== "image" && !displayName.trim()) {
      alert("Please enter a display name for PDF/Video.");
      return;
    }

    try {
      setValidationLoading(true);
      setError(null);

      const payload = {
        photoId: photo.id,
        decision: decision ? "valider" : "refuser",
        rejectReason: reason,
        classification: decision ? classification : null,
        artworkId: decision && artworkId ? artworkId : null,
        newFilename: newFilename !== photo.filename ? newFilename : null,
        generatePerspective: generatePerspective,
        backgroundName: selectedBackground,
        displayName: displayName,
      };

      const response = await fetch("/api/photos/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify(payload),
      });

      // if (!response.ok) {
      //   const errorData = await response.json();
      //   throw new Error(errorData.error || `Error ${response.status}`);
      // }
      if (response.status === 409) {
        // duplicate found
        const data = await response.json();
        setDuplicateData(data);
        setShowDuplicateModal(true);
        setValidationLoading(false);
        return; // STOP normal validation
      }

      if (!response.ok) {
        const errorData = await response.json();
        setValidationDisabled(true);
        throw new Error(errorData.error || `Error ${response.status}`);
      }

      // Update photo status
      photo.status = decision ? "validated" : "rejected";

      // Reset forms
      setShowRejectForm(false);
      setRejectReason("");
      setCustomReason("");

      // Call parent callback if provided
      if (onValidate) {
        onValidate(photo, decision, reason);
      }
      alert("Image validated successfully");
      if (window.setAppView) {
      window.setAppView("validated");
    }

    } catch (err) {
      setError(`Validation error: ${err.message}`);
      setValidationDisabled(true);
    } finally {
      setValidationLoading(false);
       
    }
  };
  const resolveDuplicate = async (choice) => {
    try {
      setDuplicateResolving(true);
      const token = localStorage.getItem("token");

      const payload = {
        choice,
        artworkId: duplicateData.artworkId,
        classification: duplicateData.classification,
        newFilePath: duplicateData.new.local_path,
        oldUrl: duplicateData.existing.url,
      };

      const response = await fetch("/api/photos/duplicate-resolve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (response.ok) {
        alert(result.message);

        setShowDuplicateModal(false);
        setDuplicateData(null);

        // reload updated list
        window.location.reload();
      } else {
        alert(result.error || "Resolution error");
      }
    } catch (err) {
      alert("Error resolving duplicate: " + err.message);
    } finally {
      setDuplicateResolving(false); // 🔥 STOP LOADING
    }
  };

  // Handle reject with reason
  const handleRejectSubmit = () => {
    let finalReason = rejectReason;

    if (rejectReason === "Other (specify)" && customReason) {
      finalReason = customReason;
    }

    if (!finalReason) {
      setError("Please select or enter a reason for rejection");
      return;
    }

    handleValidation(false, finalReason);
  };

  // Handle photo deletion
  const handleDeletePhoto = async () => {
    try {
      setValidationLoading(true);

      const response = await fetch(
        `/api/photos/delete?id=${encodeURIComponent(photo.id)}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      const data = await response.json();

      if (data.success) {
        alert("✅ Photo supprimée avec succès");
        // Redirect back to photos list
        if (window.onPhotoDeleted) {
          window.onPhotoDeleted();
        } else {
          window.location.href = "/";
        }
      } else {
	 throw new Error(data.message || "Error lors de la suppression");
      }
    } catch (error) {
      console.error("Error deleting photo:", error);
      alert("❌ Error lors de la suppression: " + error.message);
    } finally {
      setValidationLoading(false);
    }
  };

  // Get image URL
  // const getImageUrl = () => {
  //   if (!photo) return "";
  //   return `/api/photos/${encodeURIComponent(photo.id)}`;
  // };
  const getImageUrl = () => {
    if (!photo) return "";
    return `/api/photos/${encodeURIComponent(photo.id)}?t=${Date.now()}`;
  };

  // Get status badge
  const getStatusBadge = (status) => {
    const styles = {
      pending: "bg-yellow-100 text-yellow-800",
      validated: "bg-green-100 text-green-800",
      rejected: "bg-red-100 text-red-800",
    };

    const labels = {
      pending: "Pending",
      validated: "Validated",
      rejected: "Rejected",
    };

    return (
      <span
        className={`px-3 py-1 text-sm rounded-full ${
          styles[status] || "bg-gray-100 text-gray-800"
        }`}
      >
        {labels[status] || status}
      </span>
    );
  };

  const getDisplayFilename = (filename) => {
    if (!filename) return filename;

    const lower = filename.toLowerCase();

    // TIFF → show JPG converted version
    if (lower.endsWith(".tif") || lower.endsWith(".tiff")) {
      return filename.replace(/\.(tif|tiff)$/i, "_300dpi.jpg");
    }

    // Everything else normal
    return filename;
  };

  if (!photo) {
    return <div>No photo selected</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      {(imageLoading || replacing) && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-60 flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-white border-t-transparent mb-4"></div>
          <p className="text-white text-lg font-semibold">
            {replacing ? "Replacing image, please wait…" : "Loading image…"}
          </p>
          <p className="text-white text-sm opacity-80 mt-1">
            Large images may take a few seconds
          </p>
        </div>
      )}

      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to gallery
          </button>

          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {photo.filename}
              </h1>
              <div className="flex items-center gap-4">
                {getStatusBadge(photo.status)}
                <span className="text-gray-600">ID: {photo.id}</span>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-700">
            {error}
            <button
              onClick={() => setError(null)}
              className="float-right text-red-500 hover:text-red-700"
            >
              ×
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* File Display - Adaptive based on file type */}
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="aspect-square bg-gray-100">
              {getFileType() === "image" && (
                <div className="relative w-full h-full">
                  <img
                    src={getImageUrl()}
                    alt={photo.filename}
                    onLoad={() => setImageLoading(false)}
                    onError={() => setImageLoading(false)}
                    className="w-full h-full object-contain"
                  />

                  {/* Download Image Button */}
                  <a
                    href={`/api/photos/${encodeURIComponent(photo.id)}`}
                    download={photo.filename}
                    className="absolute top-2 right-2 px-3 py-2 bg-black bg-opacity-70 text-white rounded-md hover:bg-opacity-90 flex items-center gap-2 text-sm"
                    title="Download image"
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </a>
                </div>
              )}

              {getFileType() === "pdf" && (
                <div className="w-full h-full bg-gray-50 relative">
                  {/* PDF Preview with embedded iframe */}
                  <div className="w-full h-full">
                    <iframe
                      src={`/api/files/${encodeURIComponent(
                        photo.id
                      )}#toolbar=1&navpanes=0&scrollbar=1&view=FitH`}
                      className="w-full h-full border-0 rounded"
                      title={`PDF Preview - ${photo.filename}`}
                      onLoad={() => setImageLoading(false)}
                      onError={(e) => {
                        console.error("PDF failed to load:", e);
                        setImageLoading(false);
                        e.target.style.display = "none";
                        // Show fallback
                        const fallback = e.target.nextElementSibling;
                        if (fallback) fallback.style.display = "flex";
                      }}
                    />

                    {/* Fallback if PDF can't be displayed */}
                    <div
                      className="w-full h-full flex flex-col items-center justify-center p-6"
                      style={{ display: "none" }}
                    >
                      <div className="text-6xl mb-4">📄</div>
                      <h3 className="text-lg font-semibold mb-2">
                        {photo.filename}
                      </h3>
                      <p className="text-gray-600 text-sm mb-4">
                        Aperçu PDF non disponible
                      </p>
                    </div>
                  </div>

                  {/* PDF Controls Overlay */}
                  <div className="absolute top-2 right-2 flex gap-2">
                    <a
                      href={`/api/files/${encodeURIComponent(photo.id)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 flex items-center gap-2 text-sm shadow-md"
                      title="Ouvrir en plein écran"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 11-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 010-2h4a1 1 0 011 1v4a1 1 0 01-2 0V6.414l-2.293 2.293a1 1 0 11-1.414-1.414L13.586 5H12zm-9 7a1 1 0 012 0v1.586l2.293-2.293a1 1 0 111.414 1.414L6.414 15H8a1 1 0 010 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 010-2h1.586l-2.293-2.293a1 1 0 111.414-1.414L15 13.586V12a1 1 0 011-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Plein écran
                    </a>
                    <a
                      href={`/api/files/${encodeURIComponent(photo.id)}`}
                      download={photo.filename}
                      className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center gap-2 text-sm shadow-md"
                      title="Télécharger PDF"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Télécharger
                    </a>
                  </div>
                </div>
              )}

              {getFileType() === "video" && (
                <div className="w-full h-full bg-black relative group">
                  {/* Enhanced Video Player */}
                  <video
                    controls
                    preload="metadata"
                    className="w-full h-full object-contain"
                    poster=""
                    onLoadedMetadata={(e) => {
                      setImageLoading(false);
                      // Create thumbnail at 1 second
                      const video = e.target;
                      const canvas = document.createElement("canvas");
                      const ctx = canvas.getContext("2d");
                      canvas.width = video.videoWidth;
                      canvas.height = video.videoHeight;

                      video.currentTime = 1; // Seek to 1 second for thumbnail
                      video.addEventListener(
                        "seeked",
                        function () {
                          ctx.drawImage(
                            video,
                            0,
                            0,
                            canvas.width,
                            canvas.height
                          );
                          const thumbnail = canvas.toDataURL("image/jpeg", 0.8);
                          video.poster = thumbnail;
                          video.currentTime = 0; // Reset to beginning
                        },
                        { once: true }
                      );
                    }}
                    onError={(e) => {
                      setImageLoading(false);
                      console.error("Video failed to load:", e);
                      setError("Unable to load video");
                      // Show fallback
                      const fallback = e.target.nextElementSibling;
                      if (fallback) fallback.style.display = "flex";
                    }}
                  >
                    <source
                      src={`/api/files/${encodeURIComponent(photo.id)}`}
                    />
                    <p>Votre navigateur ne supporte pas la lecture vidéo.</p>
                  </video>

                  {/* Fallback if video can't be displayed */}
                  <div
                    className="w-full h-full flex flex-col items-center justify-center p-6 text-white"
                    style={{ display: "none" }}
                  >
                    <div className="text-6xl mb-4">🎥</div>
                    <h3 className="text-lg font-semibold mb-2">
                      {photo.filename}
                    </h3>
                    <p className="text-gray-300 text-sm mb-4">
                      Lecture vidéo non disponible
                    </p>
                    <a
                      href={`/api/files/${encodeURIComponent(photo.id)}`}
                      download={photo.filename}
                      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-2"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Télécharger vidéo
                    </a>
                  </div>

                  {/* Video Controls Overlay */}
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex gap-2">
                    <button
                      onClick={(e) => {
                        const video = e.target
                          .closest(".relative")
                          .querySelector("video");
                        if (video.requestFullscreen) {
                          video.requestFullscreen();
                        } else if (video.webkitRequestFullscreen) {
                          video.webkitRequestFullscreen();
                        }
                      }}
                      className="px-3 py-2 bg-black bg-opacity-70 text-white rounded-md hover:bg-opacity-90 flex items-center gap-2 text-sm"
                      title="Mode plein écran"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 11-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 010-2h4a1 1 0 011 1v4a1 1 0 01-2 0V6.414l-2.293 2.293a1 1 0 11-1.414-1.414L13.586 5H12zm-9 7a1 1 0 012 0v1.586l2.293-2.293a1 1 0 111.414 1.414L6.414 15H8a1 1 0 010 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 010-2h1.586l-2.293-2.293a1 1 0 111.414-1.414L15 13.586V12a1 1 0 011-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </button>
                    <a
                      href={`/api/files/${encodeURIComponent(photo.id)}`}
                      download={photo.filename}
                      className="px-3 py-2 bg-black bg-opacity-70 text-white rounded-md hover:bg-opacity-90 flex items-center gap-2 text-sm"
                      title="Télécharger vidéo"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </a>
                  </div>

                  {/* Video Info Overlay */}
                  <div className="absolute bottom-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <div className="px-3 py-2 bg-black bg-opacity-70 text-white rounded-md text-sm">
                      <div className="font-medium">{photo.filename}</div>
                      {photo.size && (
                        <div className="text-xs text-gray-300">
                          {(photo.size / (1024 * 1024)).toFixed(1)} MB
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Details and Actions */}
          <div className="space-y-6">
            {/* File Information */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-semibold flex items-center">
                  <Info className="mr-2 h-5 w-5" />
                  {getFileType() === "image" && "Information Image"}
                  {getFileType() === "pdf" && "Information Document"}
                  {getFileType() === "video" && "Information Vidéo"}
                </h2>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowRenameForm(!showRenameForm)}
                    className="flex items-center px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
                  >
                    <Edit className="h-4 w-4 mr-1" />
                    Rename
                  </button>

                  <button
                    onClick={() => setShowArtworkSearch(!showArtworkSearch)}
                    className="flex items-center px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 text-sm"
                  >
                    <Search className="h-4 w-4 mr-1" />
                    Search
                  </button>
                </div>
              </div>
              <div className="flex justify-end">
                {photo.status === "pending" && (
                  <>
                    <label
                      htmlFor="replace-file-input"
                      className={`flex items-center px-3 py-1 rounded text-sm cursor-pointer
    ${
      replacing
        ? "bg-gray-300 text-gray-500 cursor-not-allowed"
        : "bg-green-100 text-green-700 hover:bg-green-200"
    }
  `}
                    >
                      {replacing ? "⏳ Replacing…" : "🔁 Replace"}
                    </label>

                    <input
                      id="replace-file-input"
                      type="file"
                      accept="image/*,.tif,.tiff,.png,.jpg,.jpeg"
                      className="hidden"
                      onChange={async (e) => {
                        const file = e.target.files[0];
                        if (!file) return;

                        const formData = new FormData();
                        formData.append("photoId", photo.id);
                        formData.append("file", file);

                        try {
                          setReplacing(true);
                          setImageLoading(true);

                          const res = await fetch("/api/photos/replace", {
                            method: "POST",
                            headers: {
                              Authorization: `Bearer ${localStorage.getItem(
                                "token"
                              )}`,
                            },
                            body: formData,
                          });

                          const data = await res.json();
                          if (!res.ok) throw new Error(data.error);

                          // force refresh
                          setPhotoDetails(null);
                          setTimeout(() => {
                            fetchPhotoDetails();
                          }, 300);
                        } catch (err) {
                          alert("❌ Replace failed: " + err.message);
                          setImageLoading(false);
                        } finally {
                          setReplacing(false);
                          e.target.value = "";
                        }
                      }}
                    />
                  </>
                )}
              </div>
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <p className="mb-2">
                    <span className="font-medium">Name:</span> {photo.filename}
                  </p>
                  <p className="mb-2">
                    <span className="font-medium">Path:</span> {photo.id}
                  </p>
                  <p className="mb-2">
                    <span className="font-medium">Type:</span>
                    <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                      {getFileType() === "image" && "🖼️ Image"}
                      {getFileType() === "pdf" && "📄 Document PDF"}
                      {getFileType() === "video" && "🎥 Vidéo"}
                    </span>
                  </p>
                  {photo.mime_type && (
                    <p className="mb-2">
                      <span className="font-medium">Format:</span>{" "}
                      {photo.mime_type}
                    </p>
                  )}
                  <p className="mb-2">
                    <span className="font-medium">Status:</span>{" "}
                    {getStatusBadge(photo.status)}
                  </p>

                  {/* User Information */}
                  {photo.submitted_by && (
                    <p className="mb-2">
                      <span className="font-medium">Uploaded by:</span>
                      <span className="ml-2 px-2 py-1 bg-purple-100 text-purple-800 rounded text-sm">
                        📤 {photo.submitted_by}
                      </span>
                    </p>
                  )}

                  {photo.validated_by && (
                    <p className="mb-2">
                      <span className="font-medium">Validated by:</span>
                      <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                        ✅ {photo.validated_by}
                      </span>
                    </p>
                  )}

                  {photo.classification && (
                    <p className="mb-2">
                      <span className="font-medium">Classification:</span>
                      <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                        {photo.classification}
                      </span>
                    </p>
                  )}

                  {photo.reject_reason && (
                    <div className="mb-2">
                      <span className="font-medium">Rejection reason:</span>
                      <div className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                        {photo.reject_reason}
                      </div>
                    </div>
                  )}

                  {photo.validated_at && (
                    <p className="mb-2">
                      <span className="font-medium">Validation date:</span>
                      <span className="text-gray-600">
                        {new Date(photo.validated_at).toLocaleString()}
                      </span>
                    </p>
                  )}
                </div>

                {photoDetails && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">
                      Technical details
                    </h3>
                    {photo.status === "pending" ||
                    photo.status === "rejected" ? (
                      <> </>
                    ) : (
                      userRole === "admin" && (
                        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                          <h3 className="font-semibold text-green-800 mb-2">
                            ✅ Validated Image URL
                          </h3>
                          <p className="text-sm text-gray-700 mb-2">
                            Click below to quickly verify if everything is OK.
                          </p>
                          <a
                            href={`https://images.operagallery.com/FM/${getDisplayFilename(
                              photo.filename
                            )}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline break-all font-mono"
                          >
                            https://images.operagallery.com/FM/
                            {getDisplayFilename(photo.filename)}
                          </a>
                        </div>
                      )
                    )}
                    <p className="mb-2">
                      <span className="font-medium">Dimensions:</span>{" "}
                      {photoDetails.width} × {photoDetails.height} px
                    </p>
                    <p className="mb-2">
                      <span className="font-medium">Size:</span>{" "}
                      {photoDetails.size}
                    </p>
                    <p className="mb-2">
                      <span className="font-medium">Type:</span>{" "}
                      {photoDetails.type}
                    </p>
                    <p className="mb-2">
                      <span className="font-medium">Paper format:</span>{" "}
                      {photoDetails.paperFormat}
                    </p>
                  </div>
                )}
              </div>

              {/* Rename form */}
              {showRenameForm && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <form onSubmit={handleRenameSubmit}>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={newFilename}
                        onChange={(e) => setNewFilename(e.target.value)}
                        className="flex-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="New filename"
                      />
                      <button
                        type="submit"
                        className="flex items-center px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                        disabled={loading}
                      >
                        <Save className="h-4 w-4 mr-1" />
                        Save
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowRenameForm(false)}
                        className="flex items-center px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>

            {/* Artwork Search */}
            {showArtworkSearch && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <ArtworkSearch
                  photoId={photo.id}
                  onArtworkFound={handleArtworkFound}
                />

                {existingArtwork && (
                  <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
                    <h4 className="font-semibold text-green-800 mb-2">
                      Artwork found:
                    </h4>
                    <p className="text-green-700">
                      ID: {existingArtwork.IdName}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* FileMaker Data */}
            {filemakerData && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  📊 FileMaker Data
                </h2>

                {filemakerLoading ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Artwork Info */}
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-3">
                        🎨 Artwork Information
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <p className="mb-2">
                            <span className="font-medium">ID:</span>{" "}
                            {filemakerData.IdName}
                          </p>
                          <p className="mb-2">
                            <span className="font-medium">Title:</span>{" "}
                            {filemakerData.Title}
                          </p>
                          <p className="mb-2">
                            <span className="font-medium">Artist:</span>{" "}
                            {filemakerData.Artist}
                          </p>
                          <p className="mb-2">
                            <span className="font-medium">Date:</span>{" "}
                            {filemakerData.Date}
                          </p>
                        </div>
                        <div>
                          <p className="mb-2">
                            <span className="font-medium">Width:</span>{" "}
                            {filemakerData.Width} cm
                          </p>
                          <p className="mb-2">
                            <span className="font-medium">Height:</span>{" "}
                            {filemakerData.Height} cm
                          </p>
                          <p className="mb-2">
                            <span className="font-medium">Price:</span>{" "}
                            {filemakerData.Price}
                          </p>
                          <p className="mb-2">
                            <span className="font-medium">Status:</span>{" "}
                            {filemakerData.Status}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Main URLs */}
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-3">
                        🔗 Main URLs
                      </h3>
                      <div className="space-y-2">
                        {filemakerData.MAINFM && (
                          <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                            <p className="font-medium text-blue-800">
                              MAINFM (Main Image):
                            </p>
                            <a
                              href={filemakerData.MAINFM}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline text-sm break-all"
                            >
                              {filemakerData.MAINFM}
                            </a>
                          </div>
                        )}
                        {filemakerData.CertificateFMUrl && (
                          <div className="p-3 bg-green-50 border border-green-200 rounded">
                            <div className="flex items-center justify-between mb-2">
                              <p className="font-medium text-green-800">
                                CertificateFMUrl (Certificate):
                              </p>
                              <button
                                onClick={() =>
                                  downloadCertificate(filemakerData.IdName)
                                }
                                disabled={certificateDownloading}
                                className="px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
                                title="Télécharger le certificat PDF"
                              >
                                <Download className="h-3 w-3 mr-1" />
                                {certificateDownloading
                                  ? "Téléchargement..."
                                  : "Télécharger PDF"}
                              </button>
                            </div>
                            <a
                              href={filemakerData.CertificateFMUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-green-600 hover:underline text-sm break-all"
                            >
                              {filemakerData.CertificateFMUrl}
                            </a>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* 300px Images */}
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-3">
                        📸 300px Images
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[
                          "MAIN300",
                          "DET300",
                          "FACE300",
                          "DOS300",
                          "DET2300",
                          "SIGN300",
                          "DETAIL300",
                          "VERSO300",
                          "RECTO300",
                          "CLOSE300",
                          "FULL300",
                        ].map(
                          (field) =>
                            filemakerData[field] && (
                              <div
                                key={field}
                                className="p-3 bg-gray-50 border border-gray-200 rounded"
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <p className="font-medium text-gray-800">
                                    {field}:
                                  </p>
                                  <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                    FileMaker
                                  </span>
                                </div>
                                <a
                                  href={filemakerData[field]}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline text-sm break-all"
                                >
                                  {filemakerData[field]}
                                </a>
                                {/* Show image preview */}
                                <div className="mt-2">
                                  <img
                                    src={filemakerData[field]}
                                    alt={field}
                                    className="w-20 h-20 object-cover rounded border"
                                    onError={(e) => {
                                      e.target.style.display = "none";
                                    }}
                                  />
                                </div>
                              </div>
                            )
                        )}
                      </div>
                      {![
                        "MAIN300",
                        "DET300",
                        "FACE300",
                        "DOS300",
                        "SIGN300",
                        "DETAIL300",
                        "VERSO300",
                        "RECTO300",
                        "CLOSE300",
                        "FULL300",
                      ].some((field) => filemakerData[field]) && (
                        <p className="text-gray-500 italic">
                          No 300px images available
                        </p>
                      )}
                    </div>

                    {/* Certificate Info */}
                    {filemakerData.CertificateWording && (
                      <div>
                        <h3 className="font-semibold text-gray-900 mb-3">
                          📜 Certificate Information
                        </h3>
                        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
                          <p className="text-yellow-800 whitespace-pre-wrap">
                            {filemakerData.CertificateWording}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {showDuplicateModal && duplicateData && (() => {
              const em = duplicateData.existing.metrics || {};
              const nm = duplicateData.new.metrics || {};
              const eMp = em.width && em.height ? ((em.width * em.height) / 1000000).toFixed(1) : null;
              const nMp = nm.width && nm.height ? ((nm.width * nm.height) / 1000000).toFixed(1) : null;
              const eScore = (em.width * em.height || 0) * 0.6 + (em.size_mb || 0) * 0.2 + (em.quality_score || 0) * 0.2;
              const nScore = (nm.width * nm.height || 0) * 0.6 + (nm.size_mb || 0) * 0.2 + (nm.quality_score || 0) * 0.2;
              const oldIsBetter = eScore >= nScore;

              const MetricRow = ({ label, oldVal, newVal, higherIsBetter = true }) => {
                const oldNum = parseFloat(oldVal);
                const newNum = parseFloat(newVal);
                const oldWins = higherIsBetter ? oldNum >= newNum : oldNum <= newNum;
                return (
                  <tr className="border-b border-gray-100">
                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium w-24">{label}</td>
                    <td className={`py-1 px-2 text-xs text-center font-semibold ${oldWins ? "text-green-600" : "text-gray-600"}`}>
                      {oldVal ?? "—"} {oldWins && oldNum !== newNum && "✓"}
                    </td>
                    <td className={`py-1 px-2 text-xs text-center font-semibold ${!oldWins ? "text-green-600" : "text-gray-600"}`}>
                      {newVal ?? "—"} {!oldWins && oldNum !== newNum && "✓"}
                    </td>
                  </tr>
                );
              };

              return (
                <div className="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center z-50 p-4">
                  <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden">

                    {/* Header */}
                    <div className="bg-red-50 border-b border-red-200 px-6 py-4">
                      <h2 className="text-lg font-bold text-red-700 text-center">
                        ⚠ Duplicate Detected — Compare & Choose Which Photo to Keep
                      </h2>
                      <p className="text-xs text-center text-red-500 mt-1">
                        Artwork: <span className="font-semibold">{duplicateData.artworkId}</span> · Classification: <span className="font-semibold">{duplicateData.classification}</span>
                      </p>
                    </div>

                    <div className="p-6">
                      {/* Recommendation banner */}
                      <div className={`mb-4 px-4 py-2 rounded-lg text-sm font-semibold text-center ${oldIsBetter ? "bg-blue-50 text-blue-700 border border-blue-200" : "bg-green-50 text-green-700 border border-green-200"}`}>
                        {oldIsBetter
                          ? "Recommendation: The OLD image appears to have better quality"
                          : "Recommendation: The NEW image appears to have better quality"}
                      </div>

                      {/* Side by side */}
                      <div className="grid grid-cols-2 gap-6">

                        {/* OLD */}
                        <div className={`rounded-xl border-2 p-4 ${oldIsBetter ? "border-blue-400 bg-blue-50" : "border-gray-200 bg-gray-50"}`}>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-bold text-gray-700 text-sm uppercase tracking-wide">Old Image</h3>
                            {oldIsBetter && <span className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full font-semibold">Recommended</span>}
                          </div>

                          <img
                            src={duplicateData.existing.url}
                            alt="old"
                            className="w-full h-64 object-contain border rounded-lg bg-white"
                          />

                          {/* Metrics table */}
                          <div className="mt-3 bg-white rounded-lg p-3 border">
                            <table className="w-full">
                              <tbody>
                                {em.width && em.height && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Resolution</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{em.width} × {em.height} px</td>
                                  </tr>
                                )}
                                {eMp && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Megapixels</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{eMp} MP</td>
                                  </tr>
                                )}
                                {em.size_mb != null && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">File Size</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{em.size_mb} MB</td>
                                  </tr>
                                )}
                                {em.quality_score != null && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Sharpness</td>
                                    <td className="py-1 text-xs text-center">
                                      <div className="flex items-center gap-1 justify-center">
                                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                                          <div className="bg-blue-500 h-1.5 rounded-full" style={{width: `${Math.min(em.quality_score, 100)}%`}}></div>
                                        </div>
                                        <span className="font-semibold text-gray-700">{em.quality_score}</span>
                                      </div>
                                    </td>
                                  </tr>
                                )}
                                {em.faces != null && (
                                  <tr>
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Faces</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{em.faces}</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>

                          <button
                            onClick={() => resolveDuplicate("old")}
                            disabled={duplicateResolving}
                            className={`mt-4 w-full py-2.5 rounded-lg text-white font-semibold text-sm ${duplicateResolving ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"}`}
                          >
                            {duplicateResolving ? "Processing..." : "Keep OLD Image"}
                          </button>
                        </div>

                        {/* NEW */}
                        <div className={`rounded-xl border-2 p-4 ${!oldIsBetter ? "border-green-400 bg-green-50" : "border-gray-200 bg-gray-50"}`}>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-bold text-gray-700 text-sm uppercase tracking-wide">New Image</h3>
                            {!oldIsBetter && <span className="bg-green-500 text-white text-xs px-2 py-0.5 rounded-full font-semibold">Recommended</span>}
                          </div>

                          <img
                            src={`/api/photos/${encodeURIComponent(photo.id)}`}
                            alt="new"
                            className="w-full h-64 object-contain border rounded-lg bg-white"
                          />

                          {/* Metrics table */}
                          <div className="mt-3 bg-white rounded-lg p-3 border">
                            <table className="w-full">
                              <tbody>
                                {nm.width && nm.height && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Resolution</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{nm.width} × {nm.height} px</td>
                                  </tr>
                                )}
                                {nMp && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Megapixels</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{nMp} MP</td>
                                  </tr>
                                )}
                                {nm.size_mb != null && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">File Size</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{nm.size_mb} MB</td>
                                  </tr>
                                )}
                                {nm.quality_score != null && (
                                  <tr className="border-b border-gray-100">
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Sharpness</td>
                                    <td className="py-1 text-xs text-center">
                                      <div className="flex items-center gap-1 justify-center">
                                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                                          <div className="bg-green-500 h-1.5 rounded-full" style={{width: `${Math.min(nm.quality_score, 100)}%`}}></div>
                                        </div>
                                        <span className="font-semibold text-gray-700">{nm.quality_score}</span>
                                      </div>
                                    </td>
                                  </tr>
                                )}
                                {nm.faces != null && (
                                  <tr>
                                    <td className="py-1 pr-2 text-xs text-gray-500 font-medium">Faces</td>
                                    <td className="py-1 text-xs font-semibold text-center text-gray-700">{nm.faces}</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>

                          <button
                            onClick={() => resolveDuplicate("new")}
                            disabled={duplicateResolving}
                            className={`mt-4 w-full py-2.5 rounded-lg text-white font-semibold text-sm ${duplicateResolving ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"}`}
                          >
                            {duplicateResolving ? "Processing..." : "Use NEW Image"}
                          </button>
                        </div>
                      </div>

                      {/* Side-by-side comparison table */}
                      {(em.width || nm.width) && (
                        <div className="mt-5 bg-gray-50 rounded-xl border p-4">
                          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Side-by-Side Comparison</h4>
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-gray-200">
                                <td className="pb-2 text-xs text-gray-400 font-medium w-24"></td>
                                <td className="pb-2 text-xs font-bold text-blue-600 text-center">OLD</td>
                                <td className="pb-2 text-xs font-bold text-green-600 text-center">NEW</td>
                              </tr>
                            </thead>
                            <tbody>
                              <MetricRow label="Resolution" oldVal={em.width && em.height ? `${em.width}×${em.height}` : null} newVal={nm.width && nm.height ? `${nm.width}×${nm.height}` : null} higherIsBetter={true} />
                              <MetricRow label="Megapixels" oldVal={eMp ? `${eMp} MP` : null} newVal={nMp ? `${nMp} MP` : null} higherIsBetter={true} />
                              <MetricRow label="File Size" oldVal={em.size_mb != null ? `${em.size_mb} MB` : null} newVal={nm.size_mb != null ? `${nm.size_mb} MB` : null} higherIsBetter={true} />
                              <MetricRow label="Sharpness" oldVal={em.quality_score ?? null} newVal={nm.quality_score ?? null} higherIsBetter={true} />
                              <MetricRow label="Faces" oldVal={em.faces ?? null} newVal={nm.faces ?? null} higherIsBetter={false} />
                            </tbody>
                          </table>
                        </div>
                      )}

                      <button
                        className="mt-4 w-full py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm font-medium"
                        onClick={() => setShowDuplicateModal(false)}
                      >
                        Cancel — Decide Later
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Validation Actions */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">
                {getFileType() === "image" && "Validation Actions - Image"}
                {getFileType() === "pdf" && "Validation Actions - Document"}
                {getFileType() === "video" && "Validation Actions - Video"}
              </h2>
              {photo.status === "pending" && photo?.file_type === "image" && (
                <div className="mb-4 p-4 bg-purple-50 border border-purple-200 rounded">
                  <label className="block font-medium mb-2">
                    Perspective Image:
                  </label>

                  <div className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={generatePerspective}
                      onChange={(e) => setGeneratePerspective(e.target.checked)}
                      className="mr-2"
                    />
                    <span>Generate Perspective Image</span>
                  </div>

                  {generatePerspective && (
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Choose Background:
                      </label>

                      <select
                        value={selectedBackground}
                        onChange={(e) => setSelectedBackground(e.target.value)}
                        className="w-full px-3 py-2 border rounded"
                      >
                        <option value="">-- Select Background --</option>
                        <option value="background.png">
                          Default Background
                        </option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {/* Classification selector - Only for admins and validators */}
              {photo.status === "pending" && canValidatePhotos() && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-blue-800 mb-4">
                    📋 Classification required
                  </h3>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select the classification for this photo:
                    </label>
                    <select
                      value={classification}
                      onChange={(e) => setClassification(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">-- Choose a classification --</option>
                      {getAvailableClassifications.map((cls) => (
                        <option key={cls.value} value={cls.value}>
                          {(filledSlots.includes(cls.value) ? "● " : "○ ") +
                            cls.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Optional free-text note for the "Others" classification */}
                  {classification.startsWith("OTHERS") && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        📝 Note (optional)
                      </label>
                      <input
                        type="text"
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        placeholder="Add a note for this image…"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  )}

                  {/* Artwork ID field for PDFs and videos */}
                  {(getFileType() === "pdf" || getFileType() === "video") && (
                    <>
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          📛 Display Name (Required)
                        </label>
                        <input
                          type="text"
                          value={displayName}
                          onChange={(e) => setDisplayName(e.target.value)}
                          placeholder="Ex: Certificate of Authenticity #1"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          required
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          This name will appear in Odoo & Opera as the document
                          title
                        </p>
                      </div>
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          🎨 ID de l'œuvre à attacher (optionnel):
                        </label>
                        <input
                          type="text"
                          value={artworkId}
                          onChange={(e) =>
                            setArtworkId(e.target.value.toUpperCase())
                          }
                          placeholder="Ex: PICAPA-53866, MONET-12345..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Format: ARTISTE-NUMÉRO (ex: PICAPA-53866)
                        </p>
                      </div>
                    </>
                  )}

                  {classification && (
                    <div className="text-sm text-green-600 flex items-center">
                      ✅ Selected classification:{" "}
                      <strong className="ml-1">{classification}</strong>
                      {artworkId && (
                        <span className="ml-2">
                          • Œuvre: <strong>{artworkId}</strong>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Reject form */}
              {showRejectForm && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-red-800 mb-4 flex items-center">
                    <AlertTriangle className="h-5 w-5 mr-2" />
                    Rejection reason
                  </h3>

                  <div className="grid grid-cols-1 gap-2 mb-4">
                    {rejectReasons.map((reason) => (
                      <label key={reason} className="flex items-center">
                        <input
                          type="radio"
                          name="rejectReason"
                          value={reason}
                          checked={rejectReason === reason}
                          onChange={(e) => setRejectReason(e.target.value)}
                          className="mr-2"
                        />
                        <span className="text-sm">{reason}</span>
                      </label>
                    ))}
                  </div>

                  {rejectReason === "Autre (préciser)" && (
                    <textarea
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      placeholder="Specify rejection reason..."
                      className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
                      rows="3"
                    />
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={handleRejectSubmit}
                      disabled={validationLoading}
                      className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                    >
                      Confirm rejection
                    </button>
                    <button
                      onClick={() => setShowRejectForm(false)}
                      className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {photo.status === "pending" &&
                canValidatePhotos() &&
                !showScheduleForm && (
                  <div className="flex gap-4 opacity-100">
                    <button
                      onClick={() => setShowRejectForm(true)}
                      disabled={validationLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50"
                    >
                      <ThumbsDown className="h-5 w-5" />
                      Reject
                    </button>

                    <button
                      onClick={() => {
                        if (!classification) {
                          alert(
                            "Please first select a classification for this photo"
                          );
                          return;
                        }
                        setShowScheduleForm(true);
                      }}
                      disabled={validationLoading || validationDisabled}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                    >
                      ⏰ Schedule
                    </button>

                    <button
                      onClick={() => handleValidation(true)}
                      disabled={validationLoading || validationDisabled}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                    >
                      <ThumbsUp className="h-5 w-5" />
                      Validate Now
                    </button>
                  </div>
                )}

              {/* Schedule form */}
              {showScheduleForm && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-blue-800 mb-4 flex items-center">
                    ⏰ Schedule la publication
                  </h3>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Date et heure de publication :
                    </label>
                    <input
                      type="datetime-local"
                      value={scheduledDate}
                      onChange={(e) => setScheduledDate(e.target.value)}
                      min={new Date().toISOString().slice(0, 16)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      The photo will be automatically published to FileMaker at this date
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setShowScheduleForm(false);
                        setScheduledDate("");
                      }}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                    >
                      Annuler
                    </button>
                    <button
                      onClick={() => handleScheduledValidation()}
                      disabled={validationLoading || !scheduledDate}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Schedule
                    </button>
                  </div>
                </div>
              )}

              {photo.status === "pending" && !canValidatePhotos() && (
                <div className="text-center py-6 bg-gray-50 rounded-lg">
                  <AlertTriangle className="h-8 w-8 text-orange-500 mx-auto mb-2" />
                  <p className="text-gray-600 font-medium">
                    Pending validation
                  </p>
                  <p className="text-gray-500 text-sm">
                    Only administrators and validators can validate photos
                  </p>
                </div>
              )}

              {photo.status !== "pending" && (
                <div className="text-center py-4">
                  <p className="text-gray-600 mb-4">
                    This photo has already been{" "}
                    {photo.status === "validated" ? "validated" : "rejected"}.
                  </p>

                  {/* Actions for validated/rejected photos - Only for admins and validators */}
                  {canValidatePhotos() && (
                    <div className="flex gap-3 justify-center">
                      <button
                        onClick={() =>
                          handleValidation(photo.status !== "validated")
                        }
                        disabled={validationLoading}
                        className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                      >
                        Change to{" "}
                        {photo.status === "validated"
                          ? "rejected"
                          : "validated"}
                      </button>

                      <button
                        onClick={() => {
                          if (
                            confirm(
                              "⚠️ Are you sure you want to permanently delete this photo? This action is irreversible."
                            )
                          ) {
                            handleDeletePhoto();
                          }
                        }}
                        disabled={validationLoading}
                        className="px-6 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50 flex items-center gap-2"
                      >
                        {/* 🗑️ Supprimer la photo */}
                        🗑️ Erase the picture
                      </button>
                    </div>
                  )}

                  {!canValidatePhotos() && (
                    <p className="text-gray-500 text-sm">
                      Only administrators and validators can modify photos
                    </p>
                  )}
                </div>
              )}
              {error && (
                <div className="mt-4 p-3 bg-red-100 border border-red-300 text-red-700 text-sm rounded">
                  ⚠️ {error}
                </div>
              )}
              <div className="mt-6 flex justify-center">
                <button
                  onClick={onBack}
                  className="flex items-center gap-2 px-5 py-3 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to gallery
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
