set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
set breakpoint pending on
break canvas_core::gpu::vulkan::renderer::VulkanRenderer::draw
commands
silent
printf "NATIVE_GUI_RENDERER_DRAW_HIT\n"
bt 5
continue
end
break C_SkSurfaces_WrapBackendRenderTarget
commands
silent
printf "NATIVE_GUI_FRAMEBUFFER_SURFACE_HIT\n"
bt 5
continue
end
break vulkano::device::queue::QueueGuard::present_unchecked_locked
commands
silent
printf "NATIVE_GUI_PRESENT_HIT\n"
bt 5
continue
end
run
