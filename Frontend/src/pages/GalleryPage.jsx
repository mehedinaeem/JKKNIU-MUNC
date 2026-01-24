import { useState } from 'react';
import { galleryImages, galleryCategories } from '../data/gallery';

/**
 * GalleryPage Component
 * Photo gallery with filtering and lightbox functionality
 */
const GalleryPage = () => {
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [lightboxOpen, setLightboxOpen] = useState(false);
    const [currentImage, setCurrentImage] = useState(null);

    const filteredImages = selectedCategory === 'All'
        ? galleryImages
        : galleryImages.filter((img) => img.category === selectedCategory);

    const openLightbox = (image) => {
        setCurrentImage(image);
        setLightboxOpen(true);
        document.body.style.overflow = 'hidden';
    };

    const closeLightbox = () => {
        setLightboxOpen(false);
        setCurrentImage(null);
        document.body.style.overflow = 'unset';
    };

    const navigateImage = (direction) => {
        const currentIndex = filteredImages.findIndex((img) => img.id === currentImage.id);
        let newIndex = direction === 'prev'
            ? (currentIndex === 0 ? filteredImages.length - 1 : currentIndex - 1)
            : (currentIndex === filteredImages.length - 1 ? 0 : currentIndex + 1);
        setCurrentImage(filteredImages[newIndex]);
    };

    return (
        <div className="pt-24">
            {/* Hero */}
            <section className="bg-gradient-to-br from-primary-700 to-primary-900 text-white py-16 md:py-24">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h1 className="font-heading font-bold text-4xl md:text-5xl lg:text-6xl mb-6">Gallery</h1>
                    <p className="text-xl md:text-2xl text-white/90 max-w-3xl mx-auto">
                        Explore moments from our conferences, workshops, and community events.
                    </p>
                </div>
            </section>

            {/* Gallery */}
            <section className="section-container">
                {/* Filter */}
                <div className="flex flex-wrap justify-center gap-2 mb-12">
                    {galleryCategories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setSelectedCategory(cat)}
                            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${selectedCategory === cat ? 'bg-primary-600 text-white shadow-soft' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {filteredImages.map((image) => (
                        <div key={image.id} onClick={() => openLightbox(image)} className="relative group cursor-pointer overflow-hidden rounded-xl aspect-square">
                            <img src={image.thumbnail} alt={image.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                            <div className="absolute inset-0 bg-gradient-to-t from-primary-900/80 via-primary-900/20 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-300">
                                <div className="absolute bottom-0 left-0 right-0 p-4">
                                    <h3 className="text-white font-semibold text-sm mb-1 line-clamp-1">{image.title}</h3>
                                    <span className="text-white/70 text-xs">{image.category}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Lightbox */}
            {lightboxOpen && currentImage && (
                <div className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center" onClick={closeLightbox}>
                    <button onClick={closeLightbox} className="absolute top-4 right-4 text-white hover:text-accent-400 z-50">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); navigateImage('prev'); }} className="absolute left-4 top-1/2 -translate-y-1/2 text-white hover:text-accent-400 z-50 p-2">
                        <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); navigateImage('next'); }} className="absolute right-4 top-1/2 -translate-y-1/2 text-white hover:text-accent-400 z-50 p-2">
                        <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                    <div className="max-w-5xl max-h-[85vh] w-full mx-4" onClick={(e) => e.stopPropagation()}>
                        <img src={currentImage.src} alt={currentImage.title} className="w-full h-full object-contain rounded-lg" />
                        <div className="text-center mt-4">
                            <h3 className="text-white font-heading font-semibold text-lg">{currentImage.title}</h3>
                            <p className="text-white/60 text-sm mt-1">{currentImage.category}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default GalleryPage;
