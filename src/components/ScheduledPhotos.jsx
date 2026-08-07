// import { useEffect, useState } from "react";

// const ScheduledPhotos = () => {
//   const [photos, setPhotos] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const [currentPage, setCurrentPage] = useState(1);
//   const [totalPages, setTotalPages] = useState(1);
//   const photosPerPage = 24;

//   const fetchScheduled = async (page = 1) => {
//     setLoading(true);
//     const response = await fetch(
//       `/api/photos/list-scheduled?page=${page}&limit=${photosPerPage}`,
//       {
//         headers: {
//           Authorization: `Bearer ${localStorage.getItem("token")}`,
//         },
//       }
//     );

//     const data = await response.json();
//     setPhotos(data.photos || []);
//     setTotalPages(data.total_pages || 1);
//     setCurrentPage(page);
//     setLoading(false);
//   };

//   useEffect(() => {
//     fetchScheduled();
//   }, []);

//   return (
//     <div className="p-6">
//       <h1 className="text-2xl font-bold mb-4">
//         Scheduled Photos
//       </h1>

//       {loading ? (
//         <p>Loading...</p>
//       ) : (
//         <div className="grid grid-cols-6 gap-4">
//           {photos.map(photo => (
//             <div key={photo.id} className="border rounded p-2 bg-white shadow">

//               <img
//                 src={`/api/photos/FM/${photo.filename}`}
//                 className="w-full h-40 object-cover mb-2"
//               />

//               <div className="text-sm font-semibold truncate">
//                 {photo.filename}
//               </div>

//               <div className="text-xs text-gray-500">
//                 {new Date(photo.scheduled_date).toLocaleString()}
//               </div>

//               <div className={`mt-2 text-xs font-bold ${
//                 photo.status === "scheduled"
//                   ? "text-yellow-600"
//                   : photo.status === "completed"
//                   ? "text-green-600"
//                   : "text-red-600"
//               }`}>
//                 {photo.status === "failed"
//                   ? "❌ Failed (Rejected)"
//                   : photo.status}
//               </div>

//               {photo.error_message && (
//                 <div className="text-xs text-red-500 mt-1">
//                   {photo.error_message}
//                 </div>
//               )}

//             </div>
//           ))}
//         </div>
//       )}
//     </div>
//   );
// };

// export default ScheduledPhotos;


import React, { useState, useEffect } from "react";
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Send,
  CheckSquare,
  Square,
  Zap,
  Trash2,
} from "lucide-react";

const getUserRole = () => {
  try {
    const token = localStorage.getItem("token");
    if (!token) return null;
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role;
  } catch (e) {
    return null;
  }
};

const ScheduledPhotos = () => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPhotos, setTotalPhotos] = useState(0);

  const [releasingId, setReleasingId] = useState(null);
  const [feedback, setFeedback] = useState(null);

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkReleasing, setBulkReleasing] = useState(false);
  const [releasingAll, setReleasingAll] = useState(false);
  const [deletingAll, setDeletingAll] = useState(false);

  const userRole = getUserRole();
  const isAdmin = userRole === "admin";

  const photosPerPage = 24;

  const fetchScheduled = async (page = 1) => {
    try {
      setLoading(true);
      setError(null);

      const res = await fetch(
        `/api/photos/list-scheduled?page=${page}&limit=${photosPerPage}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      if (!res.ok) {
        throw new Error(`Error ${res.status}`);
      }

      const data = await res.json();

      setPhotos(data.photos || []);
      setTotalPages(data.total_pages || 1);
      setTotalPhotos(data.total || 0);
      setCurrentPage(page);
      setSelectedIds(new Set()); // clear selection on page change
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduled();
  }, []);

  // Per-photo release (existing behaviour)
  const releasePhoto = async (photo) => {
    const ok = window.confirm(
      `Release "${photo.filename}" now? It will be published immediately instead of waiting for ${new Date(
        photo.scheduled_date
      ).toLocaleString()}.`
    );
    if (!ok) return;

    try {
      setReleasingId(photo.id);
      setFeedback(null);

      const res = await fetch(
        `/api/admin/scheduled-uploads/${photo.id}/release`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.success === false) {
        throw new Error(data.error || `Release failed (HTTP ${res.status})`);
      }

      setFeedback({
        type: "success",
        text: `${photo.filename} released successfully`,
      });
      fetchScheduled(currentPage);
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setReleasingId(null);
    }
  };

  // Bulk release
  const releaseSelected = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    const ok = window.confirm(
      `Release ${ids.length} selected photo(s) immediately?`
    );
    if (!ok) return;

    try {
      setBulkReleasing(true);
      setFeedback(null);

      const res = await fetch("/api/admin/scheduled-uploads/release-bulk", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ ids }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.error || `Bulk release failed (HTTP ${res.status})`);
      }

      setFeedback({
        type: data.failed > 0 ? "error" : "success",
        text: data.message || `${data.released} photo(s) released`,
      });
      fetchScheduled(currentPage);
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setBulkReleasing(false);
    }
  };

  // Release ALL scheduled at once
  const releaseAll = async () => {
    const count = photos.filter((p) => p.status === "scheduled").length;
    if (count === 0) return;
    const ok = window.confirm(`Release all ${count} scheduled photo(s) immediately?`);
    if (!ok) return;
    try {
      setReleasingAll(true);
      setFeedback(null);
      const res = await fetch("/api/admin/scheduled-uploads/release-all", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Failed (HTTP ${res.status})`);
      setFeedback({
        type: data.failed > 0 ? "error" : "success",
        text: data.message || `${data.released} photo(s) released`,
      });
      fetchScheduled(currentPage);
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setReleasingAll(false);
    }
  };

  // Delete ALL scheduled at once
  const deleteAll = async () => {
    const count = photos.filter((p) => p.status === "scheduled").length;
    if (count === 0) return;
    const ok = window.confirm(
      `Delete all ${count} scheduled photo(s)? This will remove the files and cannot be undone.`
    );
    if (!ok) return;
    try {
      setDeletingAll(true);
      setFeedback(null);
      const res = await fetch("/api/admin/scheduled-uploads/delete-all", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Failed (HTTP ${res.status})`);
      setFeedback({ type: "success", text: data.message || `${data.deleted} photo(s) deleted` });
      fetchScheduled(currentPage);
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setDeletingAll(false);
    }
  };

  // Selection helpers
  const scheduledPhotos = photos.filter((p) => p.status === "scheduled");
  // Only show scheduled + failed — hide completed ones
  const visiblePhotos = photos.filter((p) => p.status === "scheduled" || p.status === "failed");

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(scheduledPhotos.map((p) => p.id)));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const allSelected =
    scheduledPhotos.length > 0 &&
    scheduledPhotos.every((p) => selectedIds.has(p.id));

  const renderStatusBadge = (status) => {
    if (status === "scheduled") {
      return (
        <div className="absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 flex items-center">
          <Clock className="w-3 h-3 mr-1" />
          Scheduled
        </div>
      );
    }

    if (status === "completed") {
      return (
        <div className="absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 flex items-center">
          <CheckCircle className="w-3 h-3 mr-1" />
          Completed
        </div>
      );
    }

    if (status === "failed") {
      return (
        <div className="absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 flex items-center">
          <XCircle className="w-3 h-3 mr-1" />
          Failed
        </div>
      );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center">
              <Clock className="w-8 h-8 text-blue-600 mr-3" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Scheduled Uploads
                </h1>
                <p className="text-gray-600">
                  Photos waiting for scheduled processing
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap justify-end">

              {/* Release selected — visible only when checkboxes used */}
              {isAdmin && selectedIds.size > 0 && (
                <button
                  onClick={releaseSelected}
                  disabled={bulkReleasing}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-medium text-sm"
                >
                  <Send className={`w-4 h-4 mr-2 ${bulkReleasing ? "animate-pulse" : ""}`} />
                  {bulkReleasing ? "Releasing..." : `Release selected (${selectedIds.size})`}
                </button>
              )}

              {/* Select / Deselect all checkboxes */}
              {isAdmin && scheduledPhotos.length > 0 && (
                <button
                  onClick={allSelected ? deselectAll : selectAll}
                  className="px-3 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 flex items-center text-sm border border-gray-200"
                >
                  {allSelected
                    ? <CheckSquare className="w-4 h-4 mr-1.5 text-blue-500" />
                    : <Square className="w-4 h-4 mr-1.5" />}
                  {allSelected ? "Deselect all" : "Select all"}
                </button>
              )}

              {/* Divider */}
              {isAdmin && scheduledPhotos.length > 0 && (
                <div className="h-8 w-px bg-gray-200 mx-1" />
              )}

              {/* Release ALL */}
              {isAdmin && scheduledPhotos.length > 0 && (
                <button
                  onClick={releaseAll}
                  disabled={releasingAll || deletingAll}
                  title={`Release all ${scheduledPhotos.length} scheduled photos immediately`}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm font-medium shadow-sm"
                >
                  <Zap className={`w-4 h-4 mr-2 ${releasingAll ? "animate-pulse" : ""}`} />
                  {releasingAll ? "Releasing..." : `Release all (${scheduledPhotos.length})`}
                </button>
              )}

              {/* Delete ALL */}
              {isAdmin && scheduledPhotos.length > 0 && (
                <button
                  onClick={deleteAll}
                  disabled={deletingAll || releasingAll}
                  title={`Cancel and delete all ${scheduledPhotos.length} scheduled photos`}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm font-medium shadow-sm"
                >
                  <Trash2 className={`w-4 h-4 mr-2 ${deletingAll ? "animate-pulse" : ""}`} />
                  {deletingAll ? "Deleting..." : "Delete all"}
                </button>
              )}

              {/* Refresh */}
              <button
                onClick={() => fetchScheduled(currentPage)}
                className="px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 flex items-center text-sm"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-red-800">{error}</span>
            </div>
          </div>
        )}

        {/* Action feedback */}
        {feedback && (
          <div
            className={`rounded-lg p-4 mb-6 flex items-center justify-between ${
              feedback.type === "success"
                ? "bg-green-50 border border-green-200 text-green-800"
                : "bg-red-50 border border-red-200 text-red-800"
            }`}
          >
            <div className="flex items-center">
              {feedback.type === "success" ? (
                <CheckCircle className="h-5 w-5 mr-2" />
              ) : (
                <AlertTriangle className="h-5 w-5 mr-2" />
              )}
              <span>{feedback.text}</span>
            </div>
            <button
              onClick={() => setFeedback(null)}
              className="text-lg font-bold opacity-60 hover:opacity-100"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        {/* Grid */}
        <div className="bg-white rounded-lg shadow-md p-6">

          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Scheduled Photos ({scheduledPhotos.length}
            {visiblePhotos.filter(p => p.status === "failed").length > 0 && (
              <span className="ml-2 text-base font-normal text-red-500">
                · {visiblePhotos.filter(p => p.status === "failed").length} failed
              </span>
            )})
          </h2>

          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : visiblePhotos.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600 text-lg">
                No scheduled uploads found
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                {visiblePhotos.map((photo) => {
                  const isSelected = selectedIds.has(photo.id);
                  return (
                    <div
                      key={photo.id}
                      className={`bg-white rounded-lg shadow-md overflow-hidden relative transition-all ${
                        photo.status === "scheduled" && isAdmin
                          ? isSelected
                            ? "ring-2 ring-blue-500 shadow-blue-100"
                            : "cursor-pointer hover:ring-2 hover:ring-blue-200"
                          : ""
                      }`}
                      onClick={() => {
                        if (isAdmin && photo.status === "scheduled") {
                          toggleSelect(photo.id);
                        }
                      }}
                    >
                      {/* Selection checkbox overlay */}
                      {isAdmin && photo.status === "scheduled" && (
                        <div className="absolute top-2 left-2 z-10">
                          <div
                            className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                              isSelected
                                ? "bg-blue-600 border-blue-600"
                                : "bg-white border-gray-400"
                            }`}
                          >
                            {isSelected && (
                              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 12 12">
                                <path d="M10 3L5 8.5 2 5.5" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                              </svg>
                            )}
                          </div>
                        </div>
                      )}

                      <div className="aspect-square bg-gray-100 relative">
                        {/* Status Badge */}
                        {renderStatusBadge(photo.status)}

                        {/* Thumbnail */}
                        <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                          <img
                            src={`/api/photos/scheduled/${photo.id}`}
                            alt={photo.filename}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.style.display = "none";
                            }}
                          />
                        </div>
                      </div>

                      <div className="p-3">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {photo.filename}
                        </div>

                        <div className="text-xs text-blue-600 font-mono mt-1">
                          {photo.artwork_id}
                        </div>

                        <div className="text-xs text-gray-500 mt-1">
                          {new Date(photo.scheduled_date).toLocaleString()}
                        </div>

                        {photo.status === "failed" && photo.error_message && (
                          <div className="text-xs text-red-600 mt-2">
                            {photo.error_message}
                          </div>
                        )}

                        {isAdmin && photo.status === "scheduled" && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation(); // don't toggle checkbox
                              releasePhoto(photo);
                            }}
                            disabled={releasingId === photo.id}
                            className="mt-3 w-full inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Release now (publish immediately)"
                          >
                            <Send
                              className={`h-3 w-3 mr-1 ${
                                releasingId === photo.id ? "animate-pulse" : ""
                              }`}
                            />
                            {releasingId === photo.id ? "Releasing..." : "Release now"}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-between items-center mt-6 pt-4 border-t">
                  <button
                    onClick={() => fetchScheduled(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 py-2 bg-gray-100 rounded disabled:opacity-50"
                  >
                    Previous
                  </button>

                  <span className="text-sm text-gray-600">
                    Page {currentPage} of {totalPages}
                  </span>

                  <button
                    onClick={() => fetchScheduled(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-3 py-2 bg-gray-100 rounded disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScheduledPhotos;
