(function ($) {
	
	"use strict";

	// Page loading animation

$(document).ready(function () {

    if ($.fn.owlCarousel) {

        $('.owl-features').owlCarousel({
            items:3,
            loop:true,
            dots:false,
            nav:true,
            autoplay:true,
            margin:30,
            responsive:{
                0:{ items:1 },
                800:{ items:2 },
                1000:{ items:3 },
                1800:{ items:4 }
            }
        });

        $('.owl-collection').owlCarousel({
            items:3,
            loop:true,
            dots:false,
            nav:true,
            autoplay:true,
            margin:30,
            responsive:{
                0:{ items:1 },
                800:{ items:2 },
                1000:{ items:3 }
            }
        });

        $('.owl-banner').owlCarousel({
            items:1,
            loop:true,
            dots:false,
            nav:true,
            autoplay:true,
            margin:30
        });

    } else {
        console.log("Owl Carousel not loaded");
    }

});


})(window.jQuery);