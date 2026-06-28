import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { SUBJECTS } from "../data/curriculum.js";
import noyaLogo from "../assets/noya-logo.svg";

const SubjectSelection = () => {
  const navigate = useNavigate();
  const [selectedSubject, setSelectedSubject] = useState(null);

  const handleChapterSelect = (chapter, subjectName) => {
    navigate("/chat", { state: { subject: subjectName, chapter } });
  };

  return (
    <div className="min-h-screen bg-[var(--bg)] px-4 py-12 sm:px-8">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-12 text-center animate-rise-in">
          <img src={noyaLogo} alt="" className="mx-auto mb-5 h-11 w-11 rounded-[var(--radius-sm)]" />
          <h1 className="font-[var(--font-display)] text-[36px] font-semibold tracking-tight text-[var(--ink)] sm:text-[44px]">
            Select your subject
          </h1>
          <p className="mx-auto mt-3 max-w-md text-[16px] text-[var(--ink-soft)]">
            Choose a CDC textbook, then pick the chapter you want Noya to use.
          </p>
        </header>

        {!selectedSubject ? (
          <div className="flex flex-wrap justify-center gap-4">
            {SUBJECTS.map((subject, index) => (
              <button
                key={subject.id}
                onClick={() => setSelectedSubject(subject)}
                style={{ animationDelay: `${index * 40}ms` }}
                className="animate-rise-in group relative flex h-44 w-[185px] flex-col items-start justify-between rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
              >
                <span className="marginalia text-[26px] leading-none">{subject.mark}</span>
                <span className="font-[var(--font-display)] text-[19px] font-semibold leading-snug text-[var(--ink)]">
                  {subject.name}
                </span>
                <ChevronRight
                  size={18}
                  aria-hidden="true"
                  className="absolute right-5 top-5 text-[var(--ink-faint)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[var(--pine)]"
                />
              </button>
            ))}
            <div
              className="flex h-44 w-[185px] flex-col items-center justify-center gap-1 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] bg-[var(--surface)]/50 p-5 text-center"
              aria-disabled="true"
            >
              <span className="font-[var(--font-display)] text-[17px] font-semibold leading-snug text-[var(--ink-faint)]">
                सामाजिक & नेपाली
              </span>
              <span className="text-[12px] font-medium tracking-wide text-[var(--ink-faint)]/60 uppercase">
                Coming Soon
              </span>
            </div>
          </div>
        ) : (
          <div className="animate-rise-in mx-auto max-w-2xl rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8">
            <div className="mb-7 flex items-center justify-between border-b border-[var(--border)] pb-4">
              <button
                onClick={() => setSelectedSubject(null)}
                className="flex items-center gap-1.5 rounded-[var(--radius-sm)] text-[14px] font-semibold text-[var(--ink-soft)] transition-colors hover:text-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
              >
                <ArrowLeft size={16} aria-hidden="true" /> Back to subjects
              </button>
              <div className="flex items-center gap-2.5">
                <span className="marginalia text-[20px]">{selectedSubject.mark}</span>
                <h2 className="font-[var(--font-display)] text-[20px] font-semibold text-[var(--ink)]">
                  {selectedSubject.name}
                </h2>
              </div>
            </div>

            <h3 className="mb-3 text-[12px] font-bold uppercase tracking-widest text-[var(--ink-faint)]">
              Chapters
            </h3>

            <div className="space-y-1.5">
              {selectedSubject.chapters.map((chapter) => (
                <button
                  key={chapter}
                  onClick={() => handleChapterSelect(chapter, selectedSubject.name)}
                  className="group flex w-full items-center justify-between rounded-[var(--radius-md)] border border-transparent p-3.5 text-left transition-colors hover:border-[var(--border)] hover:bg-[var(--bg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
                >
                  <span className="text-[15px] font-medium text-[var(--ink)]">{chapter}</span>
                  <ChevronRight
                    size={16}
                    aria-hidden="true"
                    className="text-[var(--ink-faint)] transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-[var(--pine)]"
                  />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SubjectSelection;
