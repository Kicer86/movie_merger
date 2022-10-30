
project(VOF LANGUAGES)

cmake_minimum_required(VERSION 3.20)

find_program(ffmpeg ffmpeg REQUIRED)
find_program(avidemux avidemux3_cli REQUIRED)
find_program(python python REQUIRED)


set(testVideos)
set(horizontalVideos "Atoms - 8579.mp4" "Frog - 113403.mp4" "Grass - 66810.mp4" "sea-waves-crashing-on-beach-shore-4793288.mp4" "Woman - 58142.mp4")
set(resolutions 2160;1080;720;360)

# convert all horizontal movies into 4 different resolutions
foreach(resolution ${resolutions})

    set(segments)
    foreach(videoFile ${horizontalVideos})
        get_filename_component(videoName ${videoFile} NAME_WE)
        set(movieFpsFileName "${videoName}-${resolution}p.mp4")
        add_custom_command(
            OUTPUT test-videos/${movieFpsFileName}
            COMMAND ${ffmpeg} -y -i ${CMAKE_CURRENT_SOURCE_DIR}/VOF-media/${videoFile} -filter:v scale=-1:${resolution} test-videos/${movieFpsFileName}
        )
        list(APPEND segments test-videos/${movieFpsFileName})
        set_source_files_properties(test-videos/${movieFpsFileName} PROPERTIES GENERATED TRUE)
    endforeach()

    # combine horizontal files into movies combining all of them (per resolution)
    set(inputFiles)
    set(first TRUE)
    foreach(videoFile ${segments})
        if(first)
            set(inputFiles ${inputFiles} --load ${videoFile})
        else()
            set(inputFiles ${inputFiles} --append ${videoFile})
        endif()
        set(first FALSE)
    endforeach()

    set(movieFileName movie-${resolution}p.mp4)
    add_custom_command(
            OUTPUT test-videos/${movieFileName}
            COMMAND ${avidemux} ${inputFiles} --video-codec Copy --save test-videos/${movieFileName}
            DEPENDS ${segments}
        )
    list(APPEND testVideos test-videos/${movieFileName})

    # for 720p generate movies with various fps
    if(resolution EQUAL 720)
        set(fpsSet 120;60;30;ntsc;ntsc_film;pal;film;20)
        foreach(fps ${fpsSet})
            set(movieFpsFileName movie-${resolution}p-${fps}_fps.mp4)
            add_custom_command(
                OUTPUT test-videos/${movieFpsFileName}
                COMMAND ${ffmpeg} -y -i test-videos/movie-${resolution}p.mp4 -filter:v fps=fps=${fps} test-videos/${movieFpsFileName}
                DEPENDS test-videos/movie-${resolution}p.mp4
            )
            list(APPEND testVideos test-videos/${movieFpsFileName})
        endforeach()
    endif()

endforeach()


add_custom_target(makeVideos ALL
    DEPENDS ${testVideos}
)


enable_testing()
add_test(
    NAME same_videos_diff_fps
    COMMAND ${python}
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/same_videos_different_fps.py
            ${CMAKE_CURRENT_SOURCE_DIR}/vof.py
            ${CMAKE_CURRENT_BINARY_DIR}/test-videos
)
